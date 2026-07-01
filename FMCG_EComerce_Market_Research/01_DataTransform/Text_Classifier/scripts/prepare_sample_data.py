"""Generate synthetic sample CSV files for training and inference demo."""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SAMPLES = {
    "body cream": [
        "kem duong am body cho da kho",
        "kem duong the body mua dong",
        "kem cham soc da body 400ml",
        "kem duong am toan than huong hoa",
        "kem body lotion cap am sau",
        "kem duong da tay va chan",
        "kem body cream cho da nhay cam",
        "kem duong am body sau tam",
        "kem duong am body huong vani",
        "kem body cho da run ray",
        "kem duong am body gia re",
        "kem body cream organic",
    ],
    "shampoo": [
        "dau goi xa 2in1 cho toc kho",
        "dau goi tri gau hoa cuc",
        "dau goi phuc hoi toc hu ton",
        "dau goi cho toc dau",
        "dau goi thao duoc giam rung toc",
        "dau goi xa duong toc mem muot",
        "dau goi kich thich moc toc",
        "dau goi cho tre em khong cay mat",
        "dau goi huong hoa buoi",
        "dau goi giam gay ruc toc",
        "dau goi phong toc tu nhien",
        "dau goi herbal cho toc mong",
    ],
    "facial cleanser": [
        "sua rua mat cho da dau mun",
        "sua rua mat tao bot nhe nhang",
        "sua rua mat duong am da kho",
        "sua rua mat tri mun va tham",
        "sua rua mat sua de sua rua mat",
        "sua rua mat cho da nhay cam",
        "sua rua mat lam sach sau",
        "sua rua mat chong lao hoa",
        "sua rua mat giam dau nhan",
        "sua rua mat tao bot min",
        "sua rua mat cho nam gioi",
        "sua rua mat duong am sau rua",
    ],
    "sunscreen": [
        "kem chong nang SPF50 PA++++",
        "kem chong nang nang tone da",
        "kem chong nang cho da dau",
        "kem chong nang body chong nuoc",
        "kem chong nang vat ly cho tre em",
        "kem chong nang dang gel nhe mat",
        "kem chong nang cho da nhay cam",
        "kem chong nang chong UVA UVB",
        "kem chong nang khong bong dau",
        "kem chong nang cho da mun",
        "kem chong nang nang tone tu nhien",
        "kem chong nang di bien",
    ],
    "diaper": [
        "ta dan cho be so sinh size S",
        "ta quan cho be 9-14kg",
        "ta dan mong thoang khi",
        "ta quan chong tran dem",
        "ta dan sieu tham cho be",
        "ta quan cho be tap di",
        "ta dan cho be da nhay cam",
        "ta quan size XL cho be lon",
        "ta dan co vach bao ve",
        "ta quan mong nhe cho be",
        "ta dan cho be moi sinh",
        "ta quan chong hong dem dai",
    ],
}

PREDICT_TEXTS = [
    "kem duong am body cho be va me",
    "dau goi thao duoc giam rung toc",
    "sua rua mat tri mun cho da dau",
    "kem chong nang SPF50 cho di bien",
    "ta quan cho be 12-17kg size L",
    "serum vitamin c sang da",
]


def main() -> None:
    rows = [{"text": text, "label": label} for label, texts in SAMPLES.items() for text in texts]
    train_path = PROJECT_ROOT / "data" / "sample" / "train.csv"
    predict_path = PROJECT_ROOT / "data" / "sample" / "predict_sample.csv"

    train_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(train_path, index=False)
    pd.DataFrame({"text": PREDICT_TEXTS}).to_csv(predict_path, index=False)

    print(f"Wrote {len(rows)} training rows -> {train_path}")
    print(f"Wrote {len(PREDICT_TEXTS)} predict rows -> {predict_path}")


if __name__ == "__main__":
    main()
