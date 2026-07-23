# -*- coding: utf-8 -*-
"""Quản lý checkpoint cho crawl large-scale."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Set, Tuple


def get_checkpoint_path(data_dir: Path, run_id: str) -> Path:
    return data_dir / f"large_scale_checkpoint_{run_id}.json"


def save_checkpoint(
    checkpoint_path: Path,
    run_id: str,
    output_format: str,
    completed_categories: Set[Tuple[str, str]],
    stats: Dict[str, Any],
    writer: Any,
) -> None:
    payload = {
        "run_id": run_id,
        "updated_at": datetime.now().isoformat(),
        "output_format": output_format,
        "total_articles": int(stats.get("total_articles", 0)),
        "failed_articles": int(stats.get("failed_articles", 0)),
        "categories_done": int(stats.get("categories_done", 0)),
        "completed_categories": [
            {"source": source, "category": category}
            for source, category in sorted(completed_categories)
        ],
        "current_file_index": getattr(writer, "current_file_index", 1),
        "current_file_path": str(getattr(writer, "current_file_path", "")),
        "bytes_written": int(getattr(writer, "total_bytes_written", 0)),
    }

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_checkpoint(checkpoint_path: Path) -> Dict[str, Any]:
    if not checkpoint_path.exists():
        return {}
    with open(checkpoint_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_completed_categories(payload: Dict[str, Any]) -> Set[Tuple[str, str]]:
    completed = payload.get("completed_categories", [])
    return {
        (entry.get("source", ""), entry.get("category", ""))
        for entry in completed
        if entry.get("source") and entry.get("category")
    }
