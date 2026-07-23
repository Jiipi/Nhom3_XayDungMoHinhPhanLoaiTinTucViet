# -*- coding: utf-8 -*-
"""Tiện ích chuẩn hóa đường dẫn trong dự án."""

from __future__ import annotations

from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_data_dirs() -> List[Path]:
    """Trả về các data dir hợp lệ theo thứ tự ưu tiên."""
    return [
        PROJECT_ROOT / "data",            # preferred location
        PROJECT_ROOT / "Tool" / "data",  # legacy location
    ]


def get_data_dir(create: bool = True) -> Path:
    """
    Chọn data dir dùng chung cho toàn dự án.

    Quy tắc:
    1) Nếu có thư mục chứa dữ liệu sẵn thì dùng lại (ưu tiên data/).
    2) Nếu chưa có gì thì tạo mới tại data/ (ngoài Tool/).
    """
    for candidate in get_data_dirs():
        if candidate.exists() and candidate.is_dir():
            return candidate

    fallback = get_data_dirs()[0]
    if create:
        fallback.mkdir(parents=True, exist_ok=True)
    return fallback
