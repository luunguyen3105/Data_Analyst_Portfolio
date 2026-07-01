"""Save training summary as JSON and Markdown."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {secs:.0f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {secs:.0f}s"


def build_report_payload(
    config: dict,
    *,
    num_classes: int,
    num_samples: int,
    fit_seconds: float,
    encode_seconds: float,
    total_seconds: float,
    best_checkpoint: str | None,
    test_metrics: dict[str, Any],
    device: str,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_name": config["project_name"],
        "embedding_model": config["model"]["embedding_model_name"],
        "train_path": config["data"]["train_path"],
        "device": device,
        "num_classes": num_classes,
        "num_samples": num_samples,
        "training": {
            "epochs_configured": config["training"]["epochs"],
            "batch_size": config["training"]["batch_size"],
            "learning_rate": config["training"]["learning_rate"],
            "patience": config["training"]["patience"],
        },
        "timing": {
            "embedding_encode_seconds": round(encode_seconds, 2),
            "fit_seconds": round(fit_seconds, 2),
            "total_seconds": round(total_seconds, 2),
            "embedding_encode_human": _format_seconds(encode_seconds),
            "fit_human": _format_seconds(fit_seconds),
            "total_human": _format_seconds(total_seconds),
        },
        "best_checkpoint": best_checkpoint,
        "test_metrics": test_metrics,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    metrics = report.get("test_metrics") or {}
    metric_lines = "\n".join(
        f"| {key} | {value:.4f} |" if isinstance(value, float) else f"| {key} | {value} |"
        for key, value in sorted(metrics.items())
    )
    if not metric_lines:
        metric_lines = "| _(no test metrics)_ | — |"

    checkpoint = report.get("best_checkpoint") or "—"
    return f"""# Training Report — {report["project_name"]}

_Generated: {report["generated_at_utc"]}_

## Run summary

| Field | Value |
|-------|-------|
| Embedding model | `{report["embedding_model"]}` |
| Device | {report["device"]} |
| Training samples | {report["num_samples"]} |
| Number of classes | {report["num_classes"]} |
| Train CSV | `{report["train_path"]}` |
| Best checkpoint | `{checkpoint}` |

## Training time

| Stage | Duration |
|-------|----------|
| Text embedding (encode) | {report["timing"]["embedding_encode_human"]} |
| Classifier training (fit) | {report["timing"]["fit_human"]} |
| **Total** | **{report["timing"]["total_human"]}** |

## Test metrics

| Metric | Value |
|--------|-------|
{metric_lines}

## Which model should I use?

See [docs/MODEL_RECOMMENDATION.md](../../docs/MODEL_RECOMMENDATION.md) for accuracy vs speed trade-offs across embedding models.

Quick guide:
- **Portfolio / CPU demo** → `paraphrase-multilingual-MiniLM-L12-v2` (`demo_config.yaml`)
- **Production Vietnamese text** → `namdp-ptit/ViDense` or `BAAI/bge-m3`
- **Best accuracy (GPU ≥ 16GB)** → `Qwen/Qwen3-Embedding-8B`
"""


def save_training_report(output_dir: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "training_report.json"
    md_path = output_dir / "training_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown_report(report))

    return json_path, md_path
