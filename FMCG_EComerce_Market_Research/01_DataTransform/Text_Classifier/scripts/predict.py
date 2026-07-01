"""Run inference with a trained product text classifier."""

import argparse
import sys
from pathlib import Path
from typing import Any

import lightning as L
import pandas as pd
import torch
from torch.nn import CrossEntropyLoss

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from helper.logger_helper import LoggerSimple
from src.label_handler import load_label_map
from src.lightning_module import TextClassifierModule
from src.models.embedders import get_embedder
from src.paths import resolve_path
from src.utils import load_config

logger = LoggerSimple(name=__name__).logger


def predict(
    texts: list[str],
    model: L.LightningModule,
    embedder,
    device: str,
    id_to_label: dict[int, str],
    top_k: int = 2,
) -> list[dict[str, Any]]:
    model.eval()
    results = []
    with torch.no_grad():
        embeddings = embedder.encode(texts).to(device)
        logits = model(embeddings)
        probabilities = torch.softmax(logits, dim=1)
        top_k_probs, top_k_indices = torch.topk(probabilities, min(top_k, probabilities.shape[1]), dim=1)

        for i in range(len(texts)):
            preds = {}
            for j in range(top_k_indices.shape[1]):
                pred_idx = top_k_indices[i, j].item()
                preds[f"pred_{j + 1}_label"] = id_to_label.get(pred_idx, "unknown")
                preds[f"pred_{j + 1}_score"] = round(top_k_probs[i, j].item(), 4)
            results.append(preds)
    return results


def main(
    checkpoint_path: str,
    config_path: str,
    input_path: str,
    output_path: str,
    text_column: str,
    top_k: int,
) -> None:
    config = load_config(config_path)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    project_name = config["project_name"]
    output_dir = resolve_path(config["data"]["output_dir"]) / project_name
    label_map_path = output_dir / "label_map.json"
    id_to_label, _ = load_label_map(str(label_map_path))
    num_classes = len(id_to_label)

    embedder = get_embedder(model_name=config["model"]["embedding_model_name"], device=device)
    loss_fn = CrossEntropyLoss()
    model = TextClassifierModule.load_from_checkpoint(
        checkpoint_path,
        map_location=device,
        embedding_dim=embedder.embedding_dim,
        num_classes=num_classes,
        dropout=config["model"]["classifier_head"]["dropout"],
        learning_rate=config["training"]["learning_rate"],
        config=config,
        loss_fn=loss_fn,
        weight_decay=config["training"]["weight_decay"],
    )
    model.eval()

    df = pd.read_csv(input_path)
    if text_column not in df.columns:
        raise ValueError(f"Column '{text_column}' not found. Available: {list(df.columns)}")

    texts = df[text_column].astype(str).tolist()
    predictions = predict(texts, model, embedder, device, id_to_label, top_k=top_k)
    df_out = pd.concat([df, pd.DataFrame(predictions)], axis=1)

    output_path = resolve_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)
    logger.info(f"Saved predictions -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict product categories from text.")
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to .ckpt file (e.g. output/product_category_demo/models/best-model-....ckpt)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(PROJECT_ROOT / "configs" / "base_config.yaml"),
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(PROJECT_ROOT / "data" / "sample" / "predict_sample.csv"),
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "output" / "predictions.csv"),
    )
    parser.add_argument("--text-column", type=str, default="text")
    parser.add_argument("--top-k", type=int, default=2)
    args = parser.parse_args()

    main(
        checkpoint_path=str(resolve_path(args.checkpoint)),
        config_path=str(resolve_path(args.config)),
        input_path=str(resolve_path(args.input)),
        output_path=str(resolve_path(args.output)),
        text_column=args.text_column,
        top_k=args.top_k,
    )
