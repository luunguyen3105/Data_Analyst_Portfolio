"""Train a product text classifier."""

import argparse
import os
import sys
import time
from pathlib import Path

import lightning as L
import pandas as pd
import torch
import torch.nn as nn
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch import loggers as pl_loggers

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from helper.logger_helper import LoggerSimple
from src.data_module import TextDataModule
from src.label_handler import create_label_maps, save_label_map
from src.lightning_module import TextClassifierModule
from src.models.embedders import get_embedder
from src.paths import resolve_path
from src.training_report import build_report_payload, save_training_report
from src.utils import load_config, set_seed

logger = LoggerSimple(name=__name__).logger
torch.set_float32_matmul_precision("medium")


def _count_training_samples(train_path: str, config: dict) -> int:
    df = pd.read_csv(train_path)
    df = df[df["text"].notna() & df["label"].notna()]
    counts = df["label"].value_counts()
    df = df[df["label"].map(counts) >= config["data"]["min_label_count"]]
    df = df.drop_duplicates(subset=["text", "label"], keep="first")
    df = df.groupby("label", group_keys=False).head(config["data"]["max_label_count"])
    return len(df)


def main(config_path: str) -> None:
    total_start = time.perf_counter()
    config = load_config(config_path)
    set_seed(config["reproducibility"]["seed"])

    embedding_model_name = config["model"]["embedding_model_name"]
    project_name = config["project_name"]
    output_dir = resolve_path(config["data"]["output_dir"]) / project_name
    output_log_dir = resolve_path(config["data"]["output_dir"]) / "logs"
    output_model_dir = output_dir / "models"
    train_path = str(resolve_path(config["data"]["train_path"]))
    device = "cuda" if torch.cuda.is_available() else "cpu"

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(output_log_dir, exist_ok=True)
    os.makedirs(output_model_dir, exist_ok=True)

    logger.info(f"Training data: {train_path}")
    label_to_id, id_to_label, num_classes = create_label_maps(train_path)
    num_samples = _count_training_samples(train_path, config)
    logger.info(
        f"Found {num_classes} classes, {num_samples} samples "
        f"(min={config['data']['min_label_count']}, max={config['data']['max_label_count']} per label)"
    )
    save_label_map(id_to_label, output_dir / "label_map.json")

    embedder = get_embedder(model_name=embedding_model_name, device=device)

    loss_fn = nn.CrossEntropyLoss()
    model = TextClassifierModule(
        embedding_dim=embedder.embedding_dim,
        num_classes=num_classes,
        learning_rate=config["training"]["learning_rate"],
        dropout=config["model"]["classifier_head"]["dropout"],
        loss_fn=loss_fn,
        config=config,
        weight_decay=config["training"]["weight_decay"],
    )

    checkpoint_callback = ModelCheckpoint(
        monitor="val_MulticlassAccuracy",
        dirpath=str(output_model_dir),
        filename="best-model-{epoch:02d}-{val_loss:.2f}",
        save_top_k=1,
        mode="max",
    )
    early_stopping_callback = EarlyStopping(
        monitor="val_MulticlassAccuracy",
        patience=config["training"]["patience"],
        mode="max",
    )

    tb_logger = pl_loggers.TensorBoardLogger(
        save_dir=str(output_log_dir),
        name=f"{project_name}-{embedding_model_name.replace('/', '-')}",
    )

    trainer = L.Trainer(
        accelerator="gpu" if torch.cuda.is_available() else "cpu",
        max_epochs=config["training"]["epochs"],
        callbacks=[checkpoint_callback, early_stopping_callback],
        logger=[tb_logger],
        enable_progress_bar=True,
        log_every_n_steps=5,
        num_sanity_val_steps=0,
        deterministic=True,
        inference_mode=False,
    )

    data_module = TextDataModule(
        file_path=train_path,
        label_to_id=label_to_id,
        batch_size=config["training"]["batch_size"],
        seed=config["reproducibility"]["seed"],
        embedder=embedder,
        min_label_count=config["data"]["min_label_count"],
        max_label_count=config["data"]["max_label_count"],
        max_length=config["data"]["max_length"],
    )

    encode_start = time.perf_counter()
    data_module.setup()
    encode_seconds = time.perf_counter() - encode_start

    fit_start = time.perf_counter()
    trainer.fit(model, datamodule=data_module)
    fit_seconds = time.perf_counter() - fit_start
    logger.info("Training finished.")

    test_results = trainer.test(datamodule=data_module, ckpt_path="best")
    test_metrics = test_results[0] if test_results else {}
    total_seconds = time.perf_counter() - total_start

    report = build_report_payload(
        config,
        num_classes=num_classes,
        num_samples=num_samples,
        fit_seconds=fit_seconds,
        encode_seconds=encode_seconds,
        total_seconds=total_seconds,
        best_checkpoint=checkpoint_callback.best_model_path,
        test_metrics=test_metrics,
        device=device,
    )
    json_path, md_path = save_training_report(output_dir, report)
    logger.info(f"Best checkpoint: {checkpoint_callback.best_model_path}")
    logger.info(f"Training report saved: {md_path}")
    logger.info(f"Training report (JSON): {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a product text classifier.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(PROJECT_ROOT / "configs" / "base_config.yaml"),
        help="Path to YAML config (relative to project root or absolute).",
    )
    args = parser.parse_args()
    main(str(resolve_path(args.config)))
