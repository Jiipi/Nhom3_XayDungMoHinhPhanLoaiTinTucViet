#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chuẩn bị dataset cho mô hình phân loại chủ đề tin tức:
- Đọc dữ liệu crawl (CSV/JSON/JSONL)
- Làm sạch + loại trùng + lọc độ dài
- Chuẩn hóa nhãn chủ đề liên báo
- Chia train/val/test theo stratified split
- Xuất báo cáo mất cân bằng lớp

Ví dụ:
  python scripts/prepare_dataset.py
  python scripts/prepare_dataset.py --input Tool/data/news_final_20260303_220000.csv
  python scripts/prepare_dataset.py --min-words 80 --train-ratio 0.8 --val-ratio 0.1 --test-ratio 0.1
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import hashlib
import os
import random
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from typing import Any, Dict, List, Tuple

from utils.path_utils import get_data_dir
from utils.schema import ARTICLE_FIELDS


REQUIRED_FIELDS = list(ARTICLE_FIELDS)


DEFAULT_MAPPING_CONFIG: Dict[str, Any] = {
    "canonical_labels": [
        "chinh-tri", "the-gioi", "kinh-te", "phap-luat", "giao-duc", "suc-khoe",
        "the-thao", "cong-nghe", "giai-tri", "doi-song", "du-lich", "khac",
    ],
    "label_aliases": {
        "chinh-tri": ["chinhtri", "chinh-phu", "noi-vu", "quoc-phong", "an-ninh", "dan-toc-ton-giao", "gop-y-hien-ke", "thoi-su", "thoi su"],
        "the-gioi": ["thegioi", "quoc-te", "doi-ngoai"],
        "kinh-te": ["kinhte", "kinh-doanh", "tai-chinh", "thi-truong", "chung-khoan", "dau-tu", "bat-dong-san", "dia-oc", "doanh-nghiep", "tieu-dung", "kinh-te-so"],
        "phap-luat": ["phapluat", "cong-an", "toi-pham", "an-ninh-trat-tu"],
        "giao-duc": ["giaoduc", "hoc-duong", "tuyen-sinh"],
        "suc-khoe": ["suckhoe", "y-te", "yte"],
        "the-thao": ["thethao", "bong-da"],
        "cong-nghe": ["congnghe", "khoa-hoc", "khoahoc", "khoa-hoc-cong-nghe", "startup", "oto-xe-may", "oto", "xe", "xe-may", "so-hoa", "so hoa"],
        "giai-tri": ["giaitri", "van-hoa", "am-nhac", "phim", "showbiz", "nhip-song-tre"],
        "doi-song": ["doisong", "xa-hoi", "xahoi", "gia-dinh", "tam-su", "gioi-tre", "ban-doc", "y-kien", "goc-nhin"],
        "du-lich": ["dulich"],
    },
    "label_keywords": {
        "chinh-tri": ["quoc hoi", "chinh phu", "thu tuong", "bo chinh tri", "ubnd", "quoc phong", "bo cong an"],
        "the-gioi": ["my", "trung quoc", "nga", "ukraine", "israel", "gaza", "ngoai giao", "lien hop quoc"],
        "kinh-te": ["thi truong", "co phieu", "chung khoan", "lai suat", "ngan hang", "doanh nghiep", "dau tu", "bat dong san"],
        "phap-luat": ["khoi to", "tam giam", "bi can", "xet xu", "toa an", "dieu tra", "cong an"],
        "giao-duc": ["hoc sinh", "sinh vien", "tuyen sinh", "thi tot nghiep", "dai hoc", "bo giao duc"],
        "suc-khoe": ["benh vien", "bac si", "dieu tri", "suc khoe", "thuoc", "dich benh", "bo y te"],
        "the-thao": ["bong da", "tran dau", "hlv", "giai dau", "van dong vien", "huy chuong"],
        "cong-nghe": ["ai", "cong nghe", "ung dung", "dien thoai", "chip", "phan mem", "startup", "xe dien"],
        "giai-tri": ["ca si", "dien vien", "phim", "nhac", "gameshow", "hoa hau", "giai tri"],
        "doi-song": ["doi song", "xa hoi", "gia dinh", "ban doc", "gioi tre", "tam su"],
        "du-lich": ["du lich", "diem den", "tour", "khach san", "hang khong", "visa"],
    },
    "source_overrides": {
        "baodautu": {"thoi-su-dau-tu-d1": "kinh-te", "thi-truong-dia-oc-d7": "kinh-te"},
        "vneconomy": {"dan-sinh": "doi-song", "kinh-te-the-gioi": "the-gioi"},
    },
}


@dataclass
class SplitConfig:
    train_ratio: float
    val_ratio: float
    test_ratio: float
    seed: int


def strip_accents(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_for_match(text: str) -> str:
    base = normalize_text(text).lower()
    base = strip_accents(base)
    for old, new in [("_", "-"), ("/", "-"), (".", " "), (",", " "), (":", " "), (";", " "), ("(", " "), (")", " ")]:
        base = base.replace(old, new)
    while "  " in base:
        base = base.replace("  ", " ")
    while "--" in base:
        base = base.replace("--", "-")
    return base.strip()


def load_mapping_config(path: str = "") -> Dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_MAPPING_CONFIG, ensure_ascii=False))
    if not path:
        return config
    if not os.path.exists(path):
        print(f"⚠️ Không tìm thấy mapping config: {path}. Dùng cấu hình mặc định.")
        return config
    with open(path, "r", encoding="utf-8") as f:
        user_cfg = json.load(f)

    for key in ["canonical_labels", "label_aliases", "label_keywords", "source_overrides"]:
        if key in user_cfg and user_cfg[key]:
            config[key] = user_cfg[key]
    return config


class TopicMapper:
    def __init__(self, mapping_config: Dict[str, Any], confidence_threshold: float = 0.55):
        self.cfg = mapping_config
        self.confidence_threshold = confidence_threshold
        self.canonical_labels = set(mapping_config.get("canonical_labels", []))

        self.alias_to_label: Dict[str, str] = {}
        self.keyword_by_label: Dict[str, List[str]] = {}
        self.source_overrides: Dict[str, Dict[str, str]] = {}

        for label, aliases in mapping_config.get("label_aliases", {}).items():
            if label not in self.canonical_labels:
                continue
            variants = set([label] + list(aliases or []))
            for alias in variants:
                key = normalize_for_match(alias)
                if key:
                    self.alias_to_label[key] = label

        for label, keywords in mapping_config.get("label_keywords", {}).items():
            if label in self.canonical_labels:
                self.keyword_by_label[label] = [normalize_for_match(k) for k in keywords if normalize_for_match(k)]

        for source, mapping in mapping_config.get("source_overrides", {}).items():
            source_key = normalize_for_match(source)
            self.source_overrides[source_key] = {}
            for raw_cat, label in (mapping or {}).items():
                cat_key = normalize_for_match(raw_cat)
                if label in self.canonical_labels and cat_key:
                    self.source_overrides[source_key][cat_key] = label

    def _resolve_from_override(self, source: str, raw_label: str) -> Tuple[str, str, float]:
        source_key = normalize_for_match(source)
        cat_key = normalize_for_match(raw_label)
        label = self.source_overrides.get(source_key, {}).get(cat_key)
        if label:
            return label, "source_override", 1.0
        return "", "", 0.0

    def _resolve_from_alias_or_fuzzy(self, raw_label: str) -> Tuple[str, str, float]:
        cat_key = normalize_for_match(raw_label)
        if not cat_key:
            return "", "", 0.0

        exact = self.alias_to_label.get(cat_key)
        if exact:
            return exact, "alias_exact", 0.98

        best_alias = ""
        best_label = ""
        best_score = 0.0
        for alias_key, label in self.alias_to_label.items():
            score = difflib.SequenceMatcher(None, cat_key, alias_key).ratio()
            if score > best_score:
                best_alias = alias_key
                best_label = label
                best_score = score

        if best_score >= 0.88:
            conf = min(0.92, best_score)
            return best_label, f"alias_fuzzy:{best_alias}", conf
        return "", "", 0.0

    def _resolve_from_content(self, raw_label: str, title: str, content: str, link: str) -> Tuple[str, str, float, Dict[str, int]]:
        cat_key = normalize_for_match(raw_label)
        title_key = normalize_for_match(title)
        body_key = normalize_for_match(content[:1500])
        link_key = normalize_for_match(link)

        score_by_label: Dict[str, int] = {label: 0 for label in self.keyword_by_label.keys()}
        for label, keywords in self.keyword_by_label.items():
            for kw in keywords:
                if not kw:
                    continue
                if kw in cat_key:
                    score_by_label[label] += 4
                if kw in title_key:
                    score_by_label[label] += 3
                if kw in body_key:
                    score_by_label[label] += 1
                if kw in link_key:
                    score_by_label[label] += 2

        sorted_scores = sorted(score_by_label.items(), key=lambda x: x[1], reverse=True)
        top_label, top_score = sorted_scores[0] if sorted_scores else ("", 0)
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0

        if top_score <= 0:
            return "", "", 0.0, score_by_label

        margin = top_score - second_score
        confidence = min(0.90, 0.45 + (top_score * 0.04) + (margin * 0.05))
        return top_label, "content_scoring", round(confidence, 3), score_by_label

    def map_topic(self, raw_label: str, source: str, title: str, content: str, link: str) -> Dict[str, Any]:
        label, method, confidence = self._resolve_from_override(source, raw_label)
        if label:
            return {
                "label": label,
                "method": method,
                "confidence": confidence,
                "needs_review": False,
                "scores": {},
            }

        label, method, confidence = self._resolve_from_alias_or_fuzzy(raw_label)
        if label:
            return {
                "label": label,
                "method": method,
                "confidence": confidence,
                "needs_review": confidence < self.confidence_threshold,
                "scores": {},
            }

        label, method, confidence, scores = self._resolve_from_content(raw_label, title, content, link)
        if label and confidence >= self.confidence_threshold:
            return {
                "label": label,
                "method": method,
                "confidence": confidence,
                "needs_review": False,
                "scores": scores,
            }

        return {
            "label": "khac",
            "method": "fallback_other",
            "confidence": round(confidence, 3),
            "needs_review": True,
            "scores": scores if 'scores' in locals() else {},
        }


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(str(text).split()).strip()


def normalize_slug(slug: str) -> str:
    if not slug:
        return ""
    s = str(slug).strip().lower()
    for old, new in [("_", "-"), ("/", "-"), (" ", "-")]:
        s = s.replace(old, new)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def find_latest_input(data_dir: str) -> str:
    patterns = [
        os.path.join(data_dir, "news_final_*.json"),
        os.path.join(data_dir, "news_final_*.csv"),
        os.path.join(data_dir, "news_final_*.jsonl"),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"Không tìm thấy file news_final_* trong {data_dir}. Hãy chạy crawl trước hoặc truyền --input"
        )
    return max(candidates, key=os.path.getmtime)


def load_records(input_path: str) -> List[Dict]:
    ext = os.path.splitext(input_path)[1].lower()

    if ext == ".csv":
        with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    if ext == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON đầu vào phải là list các object")
        return data

    if ext == ".jsonl":
        data = []
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data.append(json.loads(line))
        return data

    raise ValueError(f"Định dạng không hỗ trợ: {ext}. Dùng .csv / .json / .jsonl")


def validate_fields(records: List[Dict]) -> List[Dict]:
    clean = []
    for row in records:
        if not isinstance(row, dict):
            continue
        normalized = {k: normalize_text(row.get(k, "")) for k in REQUIRED_FIELDS}
        if normalized["tieu_de"] and normalized["noi_dung"]:
            clean.append(normalized)
    return clean


def filter_and_deduplicate(
    records: List[Dict],
    min_words: int,
    mapper: TopicMapper,
) -> Tuple[List[Dict], List[Dict], Counter]:
    seen = set()
    result = []
    review_rows = []
    mapping_method_counter = Counter()

    for row in records:
        text = normalize_text(row.get("noi_dung", ""))
        if len(text.split()) < min_words:
            continue

        title = normalize_text(row.get("tieu_de", ""))
        merged = f"{title}. {text}".strip().lower()
        sig = hashlib.md5(merged.encode("utf-8")).hexdigest()
        if sig in seen:
            continue
        seen.add(sig)

        label_raw = row.get("chu_de", "")
        mapping = mapper.map_topic(
            raw_label=label_raw,
            source=row.get("nguon", ""),
            title=title,
            content=text,
            link=row.get("link", ""),
        )
        label_norm = mapping["label"]
        mapping_method_counter[mapping["method"]] += 1

        row_out = {
            "chu_de": label_norm,
            "chu_de_goc": label_raw,
            "tieu_de": title,
            "noi_dung": text,
            "van_ban": f"{title}. {text}".strip(),
            "nguon": row.get("nguon", ""),
            "link": row.get("link", ""),
            "mapping_method": mapping["method"],
            "mapping_confidence": mapping["confidence"],
        }
        result.append(row_out)

        if mapping["needs_review"]:
            review_rows.append({
                "chu_de_goc": label_raw,
                "chu_de_suy_luan": label_norm,
                "mapping_method": mapping["method"],
                "mapping_confidence": mapping["confidence"],
                "nguon": row.get("nguon", ""),
                "link": row.get("link", ""),
                "tieu_de": title,
            })

    return result, review_rows, mapping_method_counter


def compute_split_counts(n: int, train_ratio: float, val_ratio: float, test_ratio: float) -> Tuple[int, int, int]:
    if n <= 1:
        return n, 0, 0
    if n == 2:
        return 1, 0, 1

    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    n_test = n - n_train - n_val

    if n_val == 0:
        n_val = 1
        n_train = max(n_train - 1, 1)
    if n_test == 0:
        n_test = 1
        n_train = max(n_train - 1, 1)

    while n_train + n_val + n_test > n:
        if n_train > 1:
            n_train -= 1
        elif n_val > 1:
            n_val -= 1
        else:
            n_test -= 1

    while n_train + n_val + n_test < n:
        n_train += 1

    return n_train, n_val, n_test


def stratified_split(records: List[Dict], cfg: SplitConfig) -> Tuple[List[Dict], List[Dict], List[Dict], Dict[str, Dict[str, int]]]:
    by_label: Dict[str, List[Dict]] = defaultdict(list)
    for row in records:
        by_label[row["chu_de"]].append(row)

    rng = random.Random(cfg.seed)
    train, val, test = [], [], []
    split_stats: Dict[str, Dict[str, int]] = {}

    for label, items in by_label.items():
        rng.shuffle(items)
        n_train, n_val, n_test = compute_split_counts(
            len(items), cfg.train_ratio, cfg.val_ratio, cfg.test_ratio
        )
        train_items = items[:n_train]
        val_items = items[n_train:n_train + n_val]
        test_items = items[n_train + n_val:n_train + n_val + n_test]

        train.extend(train_items)
        val.extend(val_items)
        test.extend(test_items)

        split_stats[label] = {
            "total": len(items),
            "train": len(train_items),
            "val": len(val_items),
            "test": len(test_items),
        }

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test, split_stats


def save_jsonl(path: str, rows: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_csv(path: str, rows: List[Dict]) -> None:
    fieldnames = [
        "chu_de", "chu_de_goc", "mapping_method", "mapping_confidence",
        "tieu_de", "noi_dung", "van_ban", "nguon", "link",
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_review_csv(path: str, rows: List[Dict]) -> None:
    if not rows:
        return
    fieldnames = ["chu_de_goc", "chu_de_suy_luan", "mapping_method", "mapping_confidence", "nguon", "link", "tieu_de"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_report(
    input_path: str,
    raw_count: int,
    valid_count: int,
    final_count: int,
    train_count: int,
    val_count: int,
    test_count: int,
    class_counts: Counter,
    split_stats: Dict[str, Dict[str, int]],
    mapping_method_counter: Counter,
    review_count: int,
) -> Dict:
    if class_counts:
        min_cls = min(class_counts.values())
        max_cls = max(class_counts.values())
        imbalance_ratio = round(max_cls / max(min_cls, 1), 2)
    else:
        imbalance_ratio = 0

    rare_classes = {k: v for k, v in class_counts.items() if v < 20}

    return {
        "input_file": input_path,
        "raw_records": raw_count,
        "valid_records": valid_count,
        "final_records": final_count,
        "splits": {
            "train": train_count,
            "val": val_count,
            "test": test_count,
        },
        "num_classes": len(class_counts),
        "class_distribution": dict(class_counts),
        "imbalance_ratio_max_div_min": imbalance_ratio,
        "rare_classes_lt_20": rare_classes,
        "split_distribution_by_class": split_stats,
        "mapping_methods": dict(mapping_method_counter),
        "low_confidence_review_count": review_count,
    }


def save_report_markdown(path: str, report: Dict) -> None:
    lines = []
    lines.append("# Báo cáo chuẩn bị dataset ML")
    lines.append("")
    lines.append(f"- Input: {report['input_file']}")
    lines.append(f"- Raw records: {report['raw_records']}")
    lines.append(f"- Valid records: {report['valid_records']}")
    lines.append(f"- Final records: {report['final_records']}")
    lines.append(f"- Số lớp: {report['num_classes']}")
    lines.append(f"- Imbalance ratio (max/min): {report['imbalance_ratio_max_div_min']}")
    lines.append("")
    lines.append("## Split")
    lines.append(f"- Train: {report['splits']['train']}")
    lines.append(f"- Val: {report['splits']['val']}")
    lines.append(f"- Test: {report['splits']['test']}")
    lines.append("")
    lines.append("## Phân bố lớp")
    for label, count in sorted(report["class_distribution"].items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {label}: {count}")

    if report.get("rare_classes_lt_20"):
        lines.append("")
        lines.append("## Lớp hiếm (<20 mẫu)")
        for label, count in sorted(report["rare_classes_lt_20"].items(), key=lambda x: (x[1], x[0])):
            lines.append(f"- {label}: {count}")

    if report.get("mapping_methods"):
        lines.append("")
        lines.append("## Mapping methods")
        for method, count in sorted(report["mapping_methods"].items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {method}: {count}")
        lines.append(f"- low_confidence_review_count: {report.get('low_confidence_review_count', 0)}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    default_data_dir = str(get_data_dir(create=True))
    parser = argparse.ArgumentParser(description="Chuẩn bị dataset cho mô hình phân loại chủ đề")
    parser.add_argument("--input", type=str, default="", help="Đường dẫn file đầu vào .csv/.json/.jsonl")
    parser.add_argument("--data-dir", type=str, default=default_data_dir, help="Thư mục dữ liệu mặc định")
    parser.add_argument("--output-dir", type=str, default=default_data_dir, help="Thư mục lưu dataset ML")
    parser.add_argument("--min-words", type=int, default=100, help="Lọc bài có số từ < min_words")
    parser.add_argument("--mapping-config", type=str, default="docs/topic_mapping.json", help="File JSON cấu hình mapping chủ đề")
    parser.add_argument("--confidence-threshold", type=float, default=0.55, help="Ngưỡng confidence để tự gán nhãn")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    ratio_sum = round(args.train_ratio + args.val_ratio + args.test_ratio, 6)
    if abs(ratio_sum - 1.0) > 1e-6:
        print("❌ Tổng train_ratio + val_ratio + test_ratio phải bằng 1.0")
        return 1

    input_path = args.input.strip() or find_latest_input(args.data_dir)
    print(f"📥 Input: {input_path}")

    raw_records = load_records(input_path)
    raw_count = len(raw_records)
    print(f"- Raw records: {raw_count}")

    valid_records = validate_fields(raw_records)
    valid_count = len(valid_records)
    print(f"- Valid records (đủ trường): {valid_count}")

    mapping_config = load_mapping_config(args.mapping_config)
    mapper = TopicMapper(mapping_config, confidence_threshold=args.confidence_threshold)

    cleaned, review_rows, mapping_method_counter = filter_and_deduplicate(
        valid_records,
        args.min_words,
        mapper,
    )
    final_count = len(cleaned)
    print(f"- Final records (lọc + dedup + min_words): {final_count}")
    print(f"- Low-confidence cần review: {len(review_rows)}")

    if final_count == 0:
        print("❌ Không còn dữ liệu sau làm sạch")
        return 1

    cfg = SplitConfig(
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    train, val, test, split_stats = stratified_split(cleaned, cfg)

    class_counts = Counter(row["chu_de"] for row in cleaned)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(args.output_dir, f"ml_dataset_{ts}")
    os.makedirs(out_dir, exist_ok=True)

    save_jsonl(os.path.join(out_dir, "train.jsonl"), train)
    save_jsonl(os.path.join(out_dir, "val.jsonl"), val)
    save_jsonl(os.path.join(out_dir, "test.jsonl"), test)

    save_csv(os.path.join(out_dir, "train.csv"), train)
    save_csv(os.path.join(out_dir, "val.csv"), val)
    save_csv(os.path.join(out_dir, "test.csv"), test)

    report = build_report(
        input_path=input_path,
        raw_count=raw_count,
        valid_count=valid_count,
        final_count=final_count,
        train_count=len(train),
        val_count=len(val),
        test_count=len(test),
        class_counts=class_counts,
        split_stats=split_stats,
        mapping_method_counter=mapping_method_counter,
        review_count=len(review_rows),
    )

    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    save_report_markdown(os.path.join(out_dir, "report.md"), report)

    with open(os.path.join(out_dir, "topic_mapping_used.json"), "w", encoding="utf-8") as f:
        json.dump(mapping_config, f, ensure_ascii=False, indent=2)

    save_review_csv(os.path.join(out_dir, "mapping_review.csv"), review_rows)

    print("\n✅ Hoàn tất chuẩn bị dataset ML")
    print(f"📁 Output: {out_dir}")
    print(f"- train/val/test JSONL + CSV đã tạo")
    print(f"- report.json + report.md đã tạo")
    print(f"- topic_mapping_used.json + mapping_review.csv đã tạo")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
