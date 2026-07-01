# LLM Product Tagging

Gán nhãn SKU e-commerce bằng **LLM + prompt + structured output** (PydanticAI).

Đây là pipeline **LLM thật** — khác hoàn toàn với [text classifier](../README.md) (embedding + MLP train trên data có nhãn).

## So sánh 2 hướng trong repo này

| | Text Classifier (`scripts/train.py`) | LLM Tagging (folder này) |
|---|---|---|
| Cơ chế | Embedding + MLP classifier | Prompt + API LLM |
| Cần data train | Có (CSV `text`, `label`) | Không (zero/few-shot qua prompt) |
| Chi phí | GPU local, 1 lần train | API call mỗi batch |
| Rule phức tạp | Khó (cần nhiều label mẫu) | Dễ mô tả trong prompt |
| Output | Label + probability | category, gender, brand + lý do |

## Files

| File | Vai trò |
|------|---------|
| `product_tagging.prompt` | System prompt — quy tắc gán category/gender/brand |
| `product_tagging.py` | Gọi LLM qua PydanticAI, batch async, export CSV |
| `data/sample_skus.csv` | 6 SKU demo (tã bỉm vs BVS vs không liên quan) |

Nguồn gốc: refactor từ pipeline nội bộ `Product_line_llm/Hapas` (đã sanitize, bỏ API key).

## Setup

```bash
cd llm-tagging
pip install pydantic-ai pandas openpyxl python-dotenv

# Copy và điền key
copy .env.example .env
```

## Chạy

```bash
python product_tagging.py
# hoặc
python product_tagging.py --input data/sample_skus.csv --category-hint "tã bỉm trẻ em" --output output/tagged_sample.csv
```

## Output columns

- `category` — nhãn category (hoặc rỗng nếu không thuộc nhóm hint)
- `gender` — nam / nữ / unisex
- `brand_tagged` — brand đã chuẩn hóa
- `signs_reasons` — keyword / lý do (audit)

## Khi nào dùng LLM vs Text Classifier?

- **LLM:** rule phức tạp, label mới thường xuyên, dataset nhỏ, cần giải thích (`signs_reasons`)
- **Text Classifier:** volume lớn, label ổn định, cần inference rẻ/nhanh/local, đã có data train

Xem thêm benchmark embedding models: [docs/MODEL_RECOMMENDATION.md](../docs/MODEL_RECOMMENDATION.md)
