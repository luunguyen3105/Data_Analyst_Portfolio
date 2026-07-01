import json
import unicodedata

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler, random_split

from helper.logger_helper import LoggerSimple
from src.models.embedders import BaseEmbedder

logger = LoggerSimple(name=__name__).logger


class TextClassificationDataset(Dataset):
    def __init__(self, embeddings: torch.Tensor, labels: list[int]):
        self.embeddings = embeddings
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.embeddings)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        return self.embeddings[idx], self.labels[idx]


def create_data_loaders(
    file_path: str,
    embedder: BaseEmbedder,
    batch_size: int,
    label_to_id: dict[str, int],
    val_split: float = 0.1,
    test_split: float = 0.1,
    seed: int = 42,
    min_label_count: int = 2,
    max_label_count: int = 100,
    max_length: int = 256,
    num_workers: int = 0,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    df = pd.read_csv(file_path)
    df["text"] = df["text"].apply(
        lambda x: unicodedata.normalize("NFKC", str(x).lower()) if x is not None else x
    )
    df["label"] = df["label"].apply(
        lambda x: unicodedata.normalize("NFKC", str(x).lower()) if x is not None else x
    )
    df = df[
        df["text"].notna()
        & df["label"].notna()
        & (df["text"].str.len() > 0)
        & (df["label"].str.len() > 0)
        & (df["label"].str.lower() != "none")
        & (df["label"].str.lower() != "nan")
    ]
    df = df[df["label"].map(df["label"].value_counts()) >= min_label_count]
    df = df.drop_duplicates(subset=["text", "label"], keep="first").reset_index(drop=True)
    df = df.groupby("label", group_keys=False).head(max_label_count).reset_index(drop=True)

    texts = df["text"].tolist()
    logger.info(f"Encoding {len(texts)} texts with batch_size={batch_size}...")
    embeddings = embedder.encode(texts, batch_size=batch_size, max_length=max_length)
    labels = [label_to_id[label] for label in df["label"]]
    dataset = TextClassificationDataset(embeddings, labels)

    dataset_size = len(dataset)
    test_size = int(test_split * dataset_size)
    val_size = int(val_split * dataset_size)
    train_size = dataset_size - test_size - val_size

    train_dataset, val_dataset, test_dataset = random_split(
        dataset,
        [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(seed),
    )

    all_labels = [dataset[i][1] for i in range(len(dataset))]
    train_labels = [all_labels[i] for i in train_dataset.indices]
    class_counts = np.bincount(train_labels)
    class_weights = 1.0 / class_counts
    sample_weights = class_weights[train_labels]
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, sampler=sampler, num_workers=num_workers
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    return train_loader, val_loader, test_loader
