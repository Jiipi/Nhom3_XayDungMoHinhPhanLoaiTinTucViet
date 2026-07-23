# -*- coding: utf-8 -*-
"""Schema/validation helpers dùng chung cho record bài báo."""

from __future__ import annotations

from typing import Any, Dict, Iterable


ARTICLE_FIELDS = ("chu_de", "tieu_de", "noi_dung", "nguon", "link")


def is_valid_article_record(article: Dict[str, Any], required_fields: Iterable[str] = ARTICLE_FIELDS) -> bool:
    if not article or not isinstance(article, dict):
        return False
    for key in required_fields:
        value = article.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return True
