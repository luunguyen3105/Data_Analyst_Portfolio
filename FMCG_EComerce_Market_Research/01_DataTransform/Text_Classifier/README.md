# Vietnamese Product Text Classifier

Embedding-based supervised text classification for e-commerce product tagging (category, brand, etc.).

This is **not** LLM prompt tagging. The pipeline uses a pretrained embedding model + a trainable MLP classifier head.

## Architecture

```
CSV (text, label) → Embedding model → Vector → MLP classifier → label + confidence
```

## Features

- Config-driven training (YAML)
- Multiple embedding backends: SentenceTransformers, BGE-M3, HuggingFace, GGUF
- PyTorch Lightning training loop with early stopping & TensorBoard
- Batch inference CLI
- Optional Streamlit demo

## Quick start

```bash
cd product-text-classifier
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt

# 1. Generate synthetic sample data
python scripts/prepare_sample_data.py

# 2. Train (GPU recommended for ViDense; or use demo_config for quick CPU run)
python scripts/train.py --config configs/base_config.yaml
# python scripts/train.py --config configs/demo_config.yaml   # MiniLM, faster

# 3. Predict (replace checkpoint path with your best .ckpt)
python scripts/predict.py ^
  --checkpoint output/product_category_demo/models/best-model-XX-val_loss=X.XX.ckpt

# After training, see results & timing:
#   output/product_category_demo/training_report.md
#   output/product_category_demo/training_report.json
# Model comparison guide: docs/MODEL_RECOMMENDATION.md

# 4. Optional: Streamlit demo
pip install streamlit
streamlit run demo/app.py
```

## Project structure

```
product-text-classifier/
├── configs/base_config.yaml   # Training & model config (same structure as original)
├── configs/demo_config.yaml   # Lightweight config for quick CPU demo
├── data/sample/               # Synthetic demo CSV (safe to publish)
├── scripts/
│   ├── prepare_sample_data.py
│   ├── train.py
│   └── predict.py
├── src/                       # Core library
├── demo/app.py                # Interactive demo
└── output/                    # Checkpoints & logs (gitignored)
```

## Model selection & benchmarks

See **[docs/MODEL_RECOMMENDATION.md](docs/MODEL_RECOMMENDATION.md)** for accuracy comparison and which embedding model to use.

Example training output (before your first run): [docs/examples/training_report.example.md](docs/examples/training_report.example.md)

After `scripts/train.py`, real metrics are saved to:
- `output/<project_name>/training_report.md`
- `output/<project_name>/training_report.json`

## Data format

Training CSV must have columns:

| text | label |
|------|-------|
| kem duong am body cho da kho | body cream |
| dau goi tri gau hoa cuc | shampoo |

Inference CSV needs a `text` column (or pass `--text-column`).

## Swap embedding model

Edit `configs/base_config.yaml`:

```yaml
model:
  embedding_model_name: "BAAI/bge-m3"           # higher quality, heavier
  # embedding_model_name: "namdp-ptit/ViDense"  # Vietnamese-focused
```

## Portfolio notes

- Sample data is **synthetic** — no client or proprietary data included.
- Replace project name / categories in README when adapting for your CV.
- Do not commit large `.ckpt` files; train locally or use Git LFS.

## Tech stack

Python 3.12 · PyTorch · PyTorch Lightning · Sentence Transformers · HuggingFace Transformers · TensorBoard
