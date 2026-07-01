# Training Report — product_category_demo (example)

_This is a sample output. Run `python scripts/train.py` to generate the real file at `output/product_category_demo/training_report.md`._

_Generated: 2026-07-01T10:00:00+00:00_

## Run summary

| Field | Value |
|-------|-------|
| Embedding model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Device | cuda |
| Training samples | 60 |
| Number of classes | 5 |
| Train CSV | `data/sample/train.csv` |
| Best checkpoint | `output/product_category_demo/models/best-model-08-val_loss=0.42.ckpt` |

## Training time

| Stage | Duration |
|-------|----------|
| Text embedding (encode) | 12.5s |
| Classifier training (fit) | 45s |
| **Total** | **58s** |

## Test metrics

| Metric | Value |
|--------|-------|
| test_MulticlassAccuracy | 0.8333 |
| test_MulticlassF1Score | 0.8200 |
| test_MulticlassPrecision | 0.8500 |
| test_MulticlassRecall | 0.8100 |
| test_loss | 0.4512 |

## Which model should I use?

See [MODEL_RECOMMENDATION.md](../MODEL_RECOMMENDATION.md) for full comparison.

- **Portfolio / CPU demo** → `demo_config.yaml` + MiniLM
- **Production Vietnamese** → `base_config.yaml` + ViDense or BGE-M3
- **Best accuracy** → Qwen3-Embedding-8B (GPU ≥ 16GB)
