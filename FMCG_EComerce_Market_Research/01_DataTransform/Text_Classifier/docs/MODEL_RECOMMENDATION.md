# Embedding model recommendation

Benchmark numbers below come from internal experiments on **real e-commerce product tagging** tasks (brand/category classification, Vietnamese product titles). Sample demo data in this repo is synthetic — re-run `scripts/train.py` on your data to refresh `output/<project>/training_report.md`.

## Summary table

| Model | Test accuracy* | Best epoch | Params | VRAM (approx.) | Encode speed | Recommended for |
|-------|----------------|------------|--------|----------------|--------------|-----------------|
| `Qwen/Qwen3-Embedding-8B` | **76.16%** | 9 | 7570M | ≥ 16 GB | Slow | Highest accuracy, production GPU |
| `BAAI/bge-m3` | 74.02% | 7 | 568M | 4–8 GB | Medium | Strong multilingual baseline |
| `GreenNode/GreenNode-Embedding-Large-VN-Mixed-V1` | 72.59% | 13 | 568M | 4–8 GB | Medium | Vietnamese-mixed corpus |
| `namdp-ptit/ViDense` | 72.30% | 16 | 560M | 4–8 GB | Medium | **Default for Vietnamese product text** |
| `intfloat/multilingual-e5-large` | 71.02% | 23 | 560M | 4–8 GB | Medium | General multilingual |
| `intfloat/multilingual-e5-base` | 70.21% | 20 | 278M | 2–4 GB | Fast | Lighter e5 variant |
| `intfloat/e5-mistral-7b-instruct` | 69.18% | 17 | 7110M | ≥ 16 GB | Slow | Not cost-effective vs Qwen3 |
| `intfloat/multilingual-e5-large-instruct` | 68.96% | 34 | 560M | 4–8 GB | Medium | Needs more epochs |
| `Salesforce/SFR-Embedding-Mistral` | 64.16% | 23 | 7110M | ≥ 16 GB | Slow | Skip for this use case |
| `Salesforce/SFR-Embedding-2_R` | 63.37% | 21 | 7110M | ≥ 16 GB | Slow | Skip for this use case |
| `paraphrase-multilingual-MiniLM-L12-v2` | ~55–65%† | varies | 118M | CPU OK | **Very fast** | Portfolio demo, prototyping |

\* Macro accuracy on held-out test split; exact number depends on dataset and label count.  
† On synthetic 60-row demo data; not comparable to production benchmarks above.

## Decision guide

### 1. Portfolio / học tập / máy không có GPU
```yaml
# configs/demo_config.yaml
embedding_model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```
- Train + infer trên CPU trong vài phút
- Đủ show pipeline end-to-end, không phải SOTA accuracy

### 2. Production — text sản phẩm tiếng Việt (khuyến nghị mặc định)
```yaml
# configs/base_config.yaml
embedding_model_name: "namdp-ptit/ViDense"
```
- Cân bằng accuracy / tài nguyên tốt cho SKU title tiếng Việt
- Cần GPU 4–8 GB; embedding encode thường chiếm 30–50% tổng thời gian train

### 3. Cần accuracy cao hơn ViDense ~2–4 điểm %
```yaml
embedding_model_name: "BAAI/bge-m3"
# hoặc
embedding_model_name: "Qwen/Qwen3-Embedding-8B"
```
- **BGE-M3**: sweet spot — gần top accuracy, model nhẹ hơn Qwen nhiều
- **Qwen3-Embedding-8B**: best accuracy trong các model đã thử; cần GPU mạnh, download & encode chậm

### 4. Dataset nhỏ (< 500 mẫu / class)
- Ưu tiên model **nhỏ** (MiniLM, e5-base) để tránh overfit classifier head
- Tăng `min_label_count`, dùng early stopping (`patience: 5`)

### 5. Dataset lớn (> 50k mẫu)
- ViDense / BGE-M3 / Qwen3
- Pre-compute embeddings once, save to disk nếu train nhiều lần (future optimization)

## Typical training time (reference)

Rough order-of-magnitude on **~5k labeled product titles**, 20–50 classes, GPU RTX 3060:

| Model | Embed ~5k texts | Train classifier (50 epochs max, early stop ~15) | Total |
|-------|-----------------|--------------------------------------------------|-------|
| MiniLM-L12-v2 | 1–3 min (CPU) | 2–5 min | **~5 min** |
| ViDense / BGE-M3 | 8–15 min | 3–8 min | **~15–25 min** |
| Qwen3-Embedding-8B | 25–45 min | 3–8 min | **~30–50 min** |

After each run, exact times are written to:
```
output/<project_name>/training_report.json
output/<project_name>/training_report.md
```

## Config mapping

| Goal | Config file | Active model |
|------|-------------|--------------|
| Demo nhanh | `configs/demo_config.yaml` | MiniLM |
| Production VN | `configs/base_config.yaml` | ViDense |
| Max accuracy | Edit `base_config.yaml` | Qwen3-Embedding-8B |

## Notes

- `freeze_embedder: true` — chỉ train MLP head; embedding model không fine-tune (ổn định, nhanh).
- Metric chính khi chọn checkpoint: `val_MulticlassAccuracy` (macro).
- So sánh model: giữ cùng `train.csv`, `seed`, `batch_size`; chỉ đổi `embedding_model_name`.
