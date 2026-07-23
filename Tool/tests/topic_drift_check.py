#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiểm tra độ lệch chủ đề trên dữ liệu crawl lớn:
- So sánh chu_de gốc với nhãn suy luận từ TopicMapper
- Báo cáo tỷ lệ lệch tổng thể + theo nguồn
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.prepare_dataset import (  # noqa: E402
    TopicMapper,
    load_mapping_config,
    normalize_for_match,
)
from utils.path_utils import get_data_dir, get_data_dirs  # noqa: E402


def resolve_data_dirs() -> list[Path]:
    dirs = []
    for p in get_data_dirs():
        if p.exists() and p.is_dir():
            dirs.append(p)
    if not dirs:
        dirs.append(get_data_dir(create=True))
    return dirs


def collect_candidate_files(data_dirs: list[Path]) -> list[Path]:
    patterns = [
        "news_crawled_*.jsonl",
        "news_final_*.jsonl",
        "news_final_*.json",
        "checkpoint_*.json",
    ]
    files: list[Path] = []
    for base in data_dirs:
        for pattern in patterns:
            files.extend(base.glob(pattern))
    files = [f for f in files if f.is_file()]
    files.sort(key=lambda p: p.stat().st_size, reverse=True)
    return files


def iter_records(path: Path):
    ext = path.suffix.lower()
    if ext == ".jsonl":
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield idx, json.loads(line)
                except Exception:
                    continue
        return

    if ext == ".json":
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for idx, row in enumerate(data, start=1):
                    if isinstance(row, dict):
                        yield idx, row
        except Exception:
            return


def run_check(input_files: list[Path], sample_limit: int = 0, confidence_threshold: float = 0.55):
    mapper = TopicMapper(load_mapping_config(""), confidence_threshold=confidence_threshold)

    total = 0
    mismatch = 0
    low_conf = 0
    by_source = defaultdict(lambda: Counter(total=0, mismatch=0, low_conf=0))
    by_raw_topic = defaultdict(lambda: Counter(total=0, mismatch=0))
    mismatch_examples = []

    alias_to_label = mapper.alias_to_label

    processed_files = 0
    for input_file in input_files:
        processed_files += 1
        for _, row in iter_records(input_file):
            raw_topic = (row.get("chu_de") or "").strip()
            title = (row.get("tieu_de") or "").strip()
            content = (row.get("noi_dung") or "").strip()
            source = (row.get("nguon") or "unknown").strip() or "unknown"
            link = (row.get("link") or "").strip()

            if not raw_topic or not title or not content:
                continue

            mapped = mapper.map_topic(raw_topic, source, title, content, link)
            predicted = mapped["label"]
            confidence = float(mapped.get("confidence", 0.0) or 0.0)

            # chuẩn hóa raw_topic về canonical label bằng alias map để so sánh công bằng
            raw_norm = normalize_for_match(raw_topic)
            expected = alias_to_label.get(raw_norm, "")

            total += 1
            by_source[source]["total"] += 1
            by_raw_topic[raw_topic]["total"] += 1

            if confidence < confidence_threshold:
                low_conf += 1
                by_source[source]["low_conf"] += 1

            # chỉ tính mismatch khi raw topic map được về canonical label
            if expected and expected != predicted:
                mismatch += 1
                by_source[source]["mismatch"] += 1
                by_raw_topic[raw_topic]["mismatch"] += 1
                if len(mismatch_examples) < 20:
                    mismatch_examples.append(
                        {
                            "source": source,
                            "raw_topic": raw_topic,
                            "expected": expected,
                            "predicted": predicted,
                            "confidence": round(confidence, 3),
                            "title": title[:160],
                        }
                    )

            if sample_limit and total >= sample_limit:
                break

        if sample_limit and total >= sample_limit:
            break

    return {
        "processed_files": processed_files,
        "input_files": [str(p) for p in input_files],
        "total_checked": total,
        "mismatch": mismatch,
        "mismatch_rate": (mismatch / total * 100) if total else 0.0,
        "low_conf": low_conf,
        "low_conf_rate": (low_conf / total * 100) if total else 0.0,
        "by_source": {
            src: {
                "total": int(c["total"]),
                "mismatch": int(c["mismatch"]),
                "mismatch_rate": (c["mismatch"] / c["total"] * 100) if c["total"] else 0.0,
                "low_conf": int(c["low_conf"]),
                "low_conf_rate": (c["low_conf"] / c["total"] * 100) if c["total"] else 0.0,
            }
            for src, c in sorted(by_source.items(), key=lambda kv: kv[1]["total"], reverse=True)
        },
        "top_raw_topic_mismatch": sorted(
            [
                {
                    "raw_topic": topic,
                    "total": int(c["total"]),
                    "mismatch": int(c["mismatch"]),
                    "mismatch_rate": (c["mismatch"] / c["total"] * 100) if c["total"] else 0.0,
                }
                for topic, c in by_raw_topic.items()
                if c["total"] >= 30
            ],
            key=lambda x: x["mismatch_rate"],
            reverse=True,
        )[:15],
        "examples": mismatch_examples,
    }


def main():
    parser = argparse.ArgumentParser(description="Kiểm tra lệch chủ đề trong dữ liệu crawl lớn")
    parser.add_argument("--input", type=str, default="", help="File JSONL cần kiểm tra")
    parser.add_argument("--sample", type=int, default=0, help="Số bản ghi kiểm tra (0 = toàn bộ file)")
    parser.add_argument("--confidence-threshold", type=float, default=0.55)
    parser.add_argument("--max-files", type=int, default=40, help="Số file lớn nhất dùng để phân tích khi không truyền --input")
    args = parser.parse_args()

    data_dirs = resolve_data_dirs()
    if not data_dirs:
        print("❌ Không tìm thấy thư mục data.")
        raise SystemExit(1)

    if args.input:
        input_files = [Path(args.input)]
    else:
        candidates = collect_candidate_files(data_dirs)
        input_files = candidates[: max(1, args.max_files)]

    if not input_files or not input_files[0].exists():
        print("❌ Không tìm thấy file dữ liệu để kiểm tra. Hãy chạy crawl trước.")
        raise SystemExit(1)

    total_mb = sum(p.stat().st_size for p in input_files) / (1024**2)
    print(f"📂 Số file kiểm tra: {len(input_files)}")
    print(f"📏 Tổng kích thước: {total_mb:.2f} MB")
    print(f"📄 File lớn nhất: {input_files[0].name}")
    if args.sample:
        print(f"🔎 Sample: {args.sample} bản ghi")

    report = run_check(input_files=input_files, sample_limit=max(0, args.sample), confidence_threshold=args.confidence_threshold)

    out_dir = data_dirs[0] / "topic_drift_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"topic_drift_{datetime_now_slug()}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n=== KẾT QUẢ LỆCH CHỦ ĐỀ ===")
    print(f"Tổng kiểm tra: {report['total_checked']}")
    print(f"Lệch chủ đề: {report['mismatch']} ({report['mismatch_rate']:.2f}%)")
    print(f"Độ tin cậy thấp: {report['low_conf']} ({report['low_conf_rate']:.2f}%)")
    print(f"Báo cáo chi tiết: {out_path}")

    print("\nTop nguồn có lệch cao:")
    top = sorted(report["by_source"].items(), key=lambda kv: kv[1]["mismatch_rate"], reverse=True)[:8]
    for src, stat in top:
        if stat["total"] < 20:
            continue
        print(f"- {src}: {stat['mismatch']}/{stat['total']} ({stat['mismatch_rate']:.2f}%), low_conf={stat['low_conf_rate']:.2f}%")


def datetime_now_slug() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    main()
