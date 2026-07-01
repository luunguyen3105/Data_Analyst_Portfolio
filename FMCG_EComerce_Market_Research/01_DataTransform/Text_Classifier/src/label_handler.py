import json
import pandas as pd
from typing import Dict, Tuple
from helper.logger_helper import LoggerSimple

logger = LoggerSimple(name=__name__).logger


def create_label_maps(file_path: str) -> Tuple[Dict[str, int], Dict[int, str], int]:
    df = pd.read_csv(file_path)
    df = df[df["label"].notna()]
    value_counts = df["label"].value_counts()
    unique_labels = value_counts.index.tolist()
    logger.info(f"Top labels by frequency: {list(zip(unique_labels, value_counts[unique_labels]))[:10]}")
    label_to_id = {label: i for i, label in enumerate(unique_labels)}
    id_to_label = {i: label for i, label in enumerate(unique_labels)}
    return label_to_id, id_to_label, len(unique_labels)


def save_label_map(id_to_label: Dict[int, str], file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(id_to_label, f, indent=4, ensure_ascii=False)


def load_label_map(file_path: str) -> Tuple[Dict[int, str], Dict[str, int]]:
    with open(file_path, "r", encoding="utf-8") as f:
        str_key_map = json.load(f)
    id_to_label = {int(k): v for k, v in str_key_map.items()}
    label_to_id = {v: k for k, v in id_to_label.items()}
    return id_to_label, label_to_id
