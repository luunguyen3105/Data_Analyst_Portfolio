"""Streamlit demo — run: streamlit run demo/app.py"""

import sys
from pathlib import Path

import streamlit as st
import torch
from torch.nn import CrossEntropyLoss

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.predict import predict
from src.label_handler import load_label_map
from src.lightning_module import TextClassifierModule
from src.models.embedders import get_embedder
from src.paths import resolve_path
from src.utils import load_config

st.set_page_config(page_title="Product Text Classifier", page_icon="🏷️")
st.title("Product Text Classifier Demo")
st.caption("Embedding + MLP classifier — not LLM prompt tagging")

config_path = PROJECT_ROOT / "configs" / "base_config.yaml"
config = load_config(str(config_path))
project_name = config["project_name"]
output_dir = resolve_path(config["data"]["output_dir"]) / project_name
model_dir = output_dir / "models"
checkpoints = sorted(model_dir.glob("*.ckpt")) if model_dir.exists() else []

if not checkpoints:
    st.warning(
        "No checkpoint found. Train first:\n\n"
        "`python scripts/prepare_sample_data.py`\n\n"
        "`python scripts/train.py --config configs/base_config.yaml`"
    )
    st.stop()

checkpoint_path = st.selectbox("Checkpoint", checkpoints, format_func=lambda p: p.name)
text = st.text_area("Product text", "kem duong am body cho da kho")
top_k = st.slider("Top-K predictions", 1, 5, 2)

if st.button("Predict"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    id_to_label, _ = load_label_map(str(output_dir / "label_map.json"))
    embedder = get_embedder(config["model"]["embedding_model_name"], device)
    model = TextClassifierModule.load_from_checkpoint(
        str(checkpoint_path),
        map_location=device,
        embedding_dim=embedder.embedding_dim,
        num_classes=len(id_to_label),
        dropout=config["model"]["classifier_head"]["dropout"],
        learning_rate=config["training"]["learning_rate"],
        config=config,
        loss_fn=CrossEntropyLoss(),
        weight_decay=config["training"]["weight_decay"],
    )
    model.eval()
    result = predict([text], model, embedder, device, id_to_label, top_k=top_k)[0]
    for i in range(1, top_k + 1):
        label = result.get(f"pred_{i}_label")
        score = result.get(f"pred_{i}_score")
        if label:
            st.metric(f"#{i} {label}", f"{score:.1%}" if score else "")
