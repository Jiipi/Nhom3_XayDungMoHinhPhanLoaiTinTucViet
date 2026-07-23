# -*- coding: utf-8 -*-
"""
VietNews AI — V4 Perfect Rewrite
=================================
- Fixes "Xe_cong_nghe" -> "xe" (gives "xe" 5,988 articles instead of 886)
- Uses class_weight="balanced" in LogisticRegression to handle class imbalance
- Uses PyVi ViTokenizer for proper Vietnamese compound word segmentation
"""

import os, sys, time, re
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from pyvi import ViTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "merged_ultra_clean_data.csv"
MODEL_SAVE_PATH = Path(__file__).resolve().parent / "news_model.joblib"

# ============================================================
# FIXED & ACCURATE LABEL MAPPING
# ============================================================
LABEL_MAP = {
    # === KINH DOANH (Business/Finance) ===
    "Kinh_doanh": "kinh-doanh",
    "Kinh-doanh": "kinh-doanh",
    "Kinh-doanh/ebank": "kinh-doanh",
    "Kinh-doanh/tien-cua-toi": "kinh-doanh",
    "Kinh-doanh/chung-khoan": "kinh-doanh",
    "Kinh-doanh/vi-mo": "kinh-doanh",
    "Kinh-doanh/doanh-nghiep": "kinh-doanh",
    "Kinh-doanh/hang-hoa": "kinh-doanh",
    "Kinh-doanh/quoc-te": "kinh-doanh",
    "Kinh-doanh/net-zero": "kinh-doanh",
    "Bat-dong-san": "kinh-doanh",
    "Lao_dong": "kinh-doanh",

    # === THỂ THAO (Sports) ===
    "The_thao": "the-thao",
    "The-thao": "the-thao",
    "The-thao/tennis": "the-thao",
    "The-thao/cac-mon-khac": "the-thao",
    "Bong-da/champions-league": "the-thao",
    "Bong-da/cac-giai-khac": "the-thao",

    # === PHÁP LUẬT (Law) ===
    "Phap_luat": "phap-luat",
    "Phap-luat": "phap-luat",

    # === THỜI SỰ (Current affairs / World) ===
    "The_gioi": "thoi-su",
    "Thoi_su": "thoi-su",
    "Thoi-su": "thoi-su",
    "The-gioi": "thoi-su",
    "The-gioi/phan-tich": "thoi-su",
    "The-gioi/tu-lieu": "thoi-su",
    "The-gioi/cuoc-song-do-day": "thoi-su",
    "The-gioi/quan-su": "thoi-su",
    "The-gioi/bac-my": "thoi-su",
    "Thoi-su/lao-dong-viec-lam": "thoi-su",
    "Thoi-su/dan-sinh": "thoi-su",
    "Thoi-su/quy-hy-vong": "thoi-su",
    "Thoi-su/giao-thong": "thoi-su",
    "Thoi-su/chinh-tri": "thoi-su",
    "Goc-nhin": "thoi-su",

    # === GIẢI TRÍ (Entertainment) ===
    "Van_hoa_giai_tri": "giai-tri",
    "Giai-tri": "giai-tri",
    "Giai-tri/sach": "giai-tri",
    "Giai-tri/lam-dep": "giai-tri",
    "Giai-tri/nhac": "giai-tri",
    "Giai-tri/san-khau-my-thuat": "giai-tri",
    "Giai-tri/phim": "giai-tri",
    "Giai-tri/gioi-sao": "giai-tri",
    "Giai-tri/thoi-trang": "giai-tri",
    "Thu-gian": "giai-tri",

    # === SỨC KHỎE (Health) ===
    "Suc_khoe_gia_dinh": "suc-khoe",
    "Suc-khoe": "suc-khoe",
    "Suc-khoe/song-khoe": "suc-khoe",
    "Suc-khoe/tin-tuc": "suc-khoe",
    "Suc-khoe/vaccine": "suc-khoe",
    "Suc-khoe/cac-benh": "suc-khoe",

    # === GIÁO DỤC (Education) ===
    "Giao_duc": "giao-duc",
    "Giao-duc": "giao-duc",
    "Giao-duc/chan-dung": "giao-duc",
    "Giao-duc/tuyen-sinh": "giao-duc",
    "Giao-duc/du-hoc": "giao-duc",
    "Giao-duc/thao-luan": "giao-duc",
    "Giao-duc/hoc-tieng-anh": "giao-duc",
    "Giao-duc/tin-tuc": "giao-duc",

    # === XE / Ô TÔ (Automotive - FIX: Xe_cong_nghe belongs to xe) ===
    "Xe_cong_nghe": "xe",
    "Xe": "xe",

    # === CÔNG NGHỆ (Technology/Science) ===
    "Cong-nghe": "cong-nghe",
    "Khoa-hoc-cong-nghe": "cong-nghe",
    "Khoa-hoc": "cong-nghe",
    "Khoa-hoc-cong-nghe/the-gioi-tu-nhien": "cong-nghe",
    "Khoa-hoc-cong-nghe/thiet-bi": "cong-nghe",
    "Khoa-hoc-cong-nghe/vu-tru": "cong-nghe",
    "Khoa-hoc-cong-nghe/chuyen-doi-so": "cong-nghe",
    "Khoa-hoc-cong-nghe/ai": "cong-nghe",
    "Khoa-hoc-cong-nghe/bo-khoa-hoc-va-cong-nghe": "cong-nghe",

    # === ĐỜI SỐNG (Lifestyle) ===
    "Nhan_ai_cong_dong": "doi-song",

    # === DU LỊCH (Travel) ===
    "Du-lich": "du-lich",
}

def map_label(raw):
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    return LABEL_MAP.get(raw, None)

def main():
    print("=" * 70)
    print("[V4 PERFECT REWRITE] LogisticRegression + Balanced Weights + PyVi")
    print("=" * 70)
    t0 = time.time()

    # 1. Load data
    print("1/5. Loading dataset...", flush=True)
    df = pd.read_csv(
        DATA_PATH, encoding="utf-8", encoding_errors="replace",
        usecols=["title", "description", "content", "text_segmented", "label"],
        low_memory=False
    )
    print(f"     Loaded {len(df):,} rows", flush=True)

    # 2. Map labels
    print("2/5. Mapping labels with fixed Xe_cong_nghe -> xe...", flush=True)
    df["mapped_label"] = df["label"].apply(map_label)
    df = df.dropna(subset=["mapped_label"])

    dist = df["mapped_label"].value_counts()
    print("     Category distribution:")
    for cat, cnt in dist.items():
        print(f"       {cat:14s}: {cnt:>6,} articles")

    # 3. Prepare text with text_segmented
    print("3/5. Preparing text features...", flush=True)
    df["text_segmented"] = df["text_segmented"].fillna("")
    df["title"] = df["title"].fillna("")
    df["description"] = df["description"].fillna("")
    df["content"] = df["content"].fillna("")

    def get_text(row):
        seg = str(row["text_segmented"]).strip()
        if len(seg) > 50:
            return seg.lower()
        full = f"{row['title']} {row['description']} {row['content']}".strip()
        return ViTokenizer.tokenize(full).lower()

    df["final_text"] = df.apply(get_text, axis=1)
    mask = df["final_text"].str.len() > 30
    df = df[mask]

    X = df["final_text"].values
    y = df["mapped_label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.1, random_state=42, stratify=y
    )
    print(f"     Train: {len(X_train):,}, Test: {len(X_test):,}", flush=True)

    # 4. Train with class_weight="balanced"
    print("4/5. Training TF-IDF + Balanced LogisticRegression...", flush=True)
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=45000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=3,
            max_df=0.90,
        )),
        ("clf", LogisticRegression(
            C=3.0,
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs"
        ))
    ])

    pipeline.fit(X_train, y_train)

    # 5. Evaluate
    print("5/5. Evaluating accuracy...", flush=True)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n     >>> BALANCED ACCURACY: {acc * 100:.2f}% <<<\n", flush=True)
    print(classification_report(y_test, y_pred, zero_division=0))

    # Save
    print(f"Saving model to {MODEL_SAVE_PATH.name}...", flush=True)
    joblib.dump(pipeline, MODEL_SAVE_PATH, compress=3)
    size_mb = MODEL_SAVE_PATH.stat().st_size / (1024 * 1024)
    print(f"Model saved: {size_mb:.1f} MB", flush=True)

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()
