"""
LLM Product Tagging (PydanticAI)
--------------------------------
Gán nhãn category / gender / brand cho SKU e-commerce bằng LLM + structured output.

Khác với text classifier (embedding + MLP): pipeline này dùng prompt + API LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIModel

try:
    from pydantic_ai.providers.azure import AzureProvider
except ImportError:
    try:
        from pydantic_ai.providers.azure_openai import AzureProvider
    except ImportError:
        AzureProvider = None  # type: ignore

LLM_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = LLM_DIR.parent
DEFAULT_PROMPT = LLM_DIR / "product_tagging.prompt"
DEFAULT_SAMPLE = LLM_DIR / "data" / "sample_skus.csv"
DEFAULT_TEMPERATURE = 0.2


# ---------------------------------------------------------------------------
# Config (env only — no hardcoded keys)
# ---------------------------------------------------------------------------


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_llm_model(temperature: float = DEFAULT_TEMPERATURE):
    endpoint = os.getenv("AZURE_GPT_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_GPT_API_KEY", "").strip()
    api_version = os.getenv("AZURE_GPT_API_VERSION", "2024-12-01-preview").strip()
    deployment = os.getenv("AZURE_GPT_DEPLOYMENT", "gpt-4o-mini").strip()

    if endpoint and api_key and AzureProvider and OpenAIChatModel:
        return OpenAIChatModel(
            model_name=deployment,
            provider=AzureProvider(
                azure_endpoint=endpoint,
                api_version=api_version,
                api_key=api_key,
            ),
            settings=ModelSettings(temperature=temperature),
        )

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        if base_url := os.getenv("OPENAI_BASE_URL", "").strip():
            os.environ["OPENAI_BASE_URL"] = base_url
        return OpenAIModel(
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            settings=ModelSettings(temperature=temperature),
        )

    raise ValueError(
        "Missing LLM credentials. Copy llm-tagging/.env.example to .env and set AZURE_GPT_* or OPENAI_API_KEY."
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SKUInput(BaseModel):
    product_base_id: str
    product_name: str
    brand: str = ""


class BatchInput(BaseModel):
    category: str = Field(..., description="Category hint from filename or config")
    skus: List[SKUInput]


class ProductTaggingOutput(BaseModel):
    product_base_id: str
    category: str
    gender: str
    brand: str
    signs_reasons: str


# ---------------------------------------------------------------------------
# LLM batch processing
# ---------------------------------------------------------------------------


async def tag_batch(
    batch: BatchInput,
    prompt_path: Path,
    temperature: float = DEFAULT_TEMPERATURE,
) -> List[ProductTaggingOutput]:
    system_prompt = prompt_path.read_text(encoding="utf-8")
    model = get_llm_model(temperature)
    agent = Agent(
        model=model,
        output_type=List[ProductTaggingOutput],
        system_prompt=system_prompt,
        retries=3,
    )
    payload = json.dumps(batch.model_dump(), ensure_ascii=False, indent=2)
    start = time.perf_counter()
    result = await agent.run(payload)
    elapsed = time.perf_counter() - start
    outputs = result.output or []
    print(f"[INFO] Tagged {len(outputs)}/{len(batch.skus)} SKU in {elapsed:.1f}s")
    return outputs


def build_batches(
    df: pd.DataFrame,
    category_hint: str,
    batch_size: int = 30,
) -> List[BatchInput]:
    skus: List[SKUInput] = []
    for _, row in df.iterrows():
        pid = str(row.get("product_base_id", "")).strip()
        name = str(row.get("product_name", "")).strip()
        brand = str(row.get("brand", "")).strip()
        if pid and name and pid.lower() != "nan":
            skus.append(SKUInput(product_base_id=pid, product_name=name, brand=brand))

    batches: List[BatchInput] = []
    for i in range(0, len(skus), batch_size):
        batches.append(BatchInput(category=category_hint, skus=skus[i : i + batch_size]))
    return batches


async def tag_dataframe(
    df: pd.DataFrame,
    category_hint: str,
    prompt_path: Path,
    batch_size: int = 30,
    max_workers: int = 3,
) -> pd.DataFrame:
    batches = build_batches(df, category_hint, batch_size)
    if not batches:
        return df

    semaphore = asyncio.Semaphore(max_workers)
    all_outputs: List[ProductTaggingOutput] = []

    async def run_one(batch: BatchInput) -> List[ProductTaggingOutput]:
        async with semaphore:
            return await tag_batch(batch, prompt_path)

    results = await asyncio.gather(*[run_one(b) for b in batches], return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"[ERROR] Batch {i + 1} failed: {res}")
            continue
        all_outputs.extend(res)

    out_df = df.copy()
    for col in ("category", "gender", "brand_tagged", "signs_reasons"):
        if col not in out_df.columns:
            out_df[col] = None

    id_to_row = {str(r["product_base_id"]): idx for idx, r in out_df.iterrows()}
    for item in all_outputs:
        idx = id_to_row.get(str(item.product_base_id))
        if idx is None:
            continue
        out_df.at[idx, "category"] = item.category
        out_df.at[idx, "gender"] = item.gender
        out_df.at[idx, "brand_tagged"] = item.brand
        out_df.at[idx, "signs_reasons"] = item.signs_reasons

    return out_df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def main_async(args: argparse.Namespace) -> None:
    load_env_file(LLM_DIR / ".env")
    load_env_file(PROJECT_ROOT / ".env")

    input_path = Path(args.input)
    prompt_path = Path(args.prompt)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path) if input_path.suffix.lower() == ".csv" else pd.read_excel(input_path)
    print(f"[INFO] Loaded {len(df)} rows from {input_path}")
    print(f"[INFO] Category hint: {args.category_hint}")

    df_out = await tag_dataframe(
        df,
        category_hint=args.category_hint,
        prompt_path=prompt_path,
        batch_size=args.batch_size,
        max_workers=args.max_workers,
    )

    if output_path.suffix.lower() == ".csv":
        df_out.to_csv(output_path, index=False)
    else:
        df_out.to_excel(output_path, index=False)
    print(f"[SUCCESS] Saved -> {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM product tagging with PydanticAI")
    parser.add_argument("--input", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    parser.add_argument("--output", default=str(LLM_DIR / "output" / "tagged_sample.csv"))
    parser.add_argument("--category-hint", default="tã bỉm trẻ em")
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--max-workers", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
