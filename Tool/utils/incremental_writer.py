# -*- coding: utf-8 -*-
"""Writer ghi dữ liệu incremental cho crawl quy mô lớn (hỗ trợ lưu đồng thời JSON + CSV)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class IncrementalWriter:
    """Ghi dữ liệu incrementally (từng bài) thay vì load hết vào memory.
    
    Hỗ trợ 3 format:
    - 'jsonl': Ghi JSON Lines (1 bài = 1 dòng)
    - 'csv': Ghi CSV  
    - 'json-csv': Ghi ĐỒNG THỜI cả JSON + CSV (tự động lưu CSV sau mỗi batch_size bài)
    """

    def __init__(self, output_dir: Path, base_filename: str, format: str = 'jsonl',
                 max_file_size_mb: int = 500, batch_size: int = 50):
        """
        Args:
            output_dir: Thư mục lưu output
            base_filename: Tên file cơ bản (không có extension)
            format: 'jsonl', 'csv', hoặc 'json-csv' (ghi cả 2)
            max_file_size_mb: Kích thước tối đa file trước khi rotate (MB)
            batch_size: Số bài để batch trước khi ghi CSV (chỉ dùng khi format='json-csv')
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_filename = base_filename
        self.format = format.lower()
        self.max_file_size_bytes = max_file_size_mb * (1024 ** 2)
        self.batch_size = batch_size

        # Cho format 'json-csv', tách thành 2 writers
        self.is_dual_format = self.format == 'json-csv'
        
        # JSONL writer state
        self.json_file_index = 1
        self.json_file_path = self._get_filepath('jsonl')
        self.json_file_size = 0
        self.json_bytes_written = 0
        
        # CSV writer state  
        self.csv_file_index = 1
        self.csv_file_path = self._get_filepath('csv')
        self.csv_file = None
        self.csv_writer = None
        self.csv_file_size = 0
        self.csv_bytes_written = 0
        self.csv_fieldnames = None
        
        # Batch buffer cho dual format
        self.batch_buffer = []
        
        # Thống kê
        self.total_articles = 0
        self.total_articles_to_csv = 0
        
        if self.format == 'jsonl' or self.format == 'json-csv':
            self._init_jsonl_file()

    @property
    def total_bytes_written(self) -> int:
        if self.format == 'jsonl':
            return self.json_bytes_written
        if self.format == 'csv':
            return self.csv_bytes_written
        return self.json_bytes_written + self.csv_bytes_written

    @property
    def current_file_index(self) -> int:
        if self.format == 'csv':
            return self.csv_file_index
        return self.json_file_index

    @property
    def current_file_path(self) -> Path:
        if self.format == 'csv':
            return self.csv_file_path
        return self.json_file_path

    @property
    def current_file_size(self) -> int:
        if self.format == 'csv':
            return self.csv_file_size
        return self.json_file_size

    def _get_filepath(self, file_format: str) -> Path:
        """Tạo tên file với index phần nếu cần."""
        if file_format == 'jsonl' and self.json_file_index == 1:
            return self.output_dir / f'{self.base_filename}.jsonl'
        elif file_format == 'jsonl':
            return self.output_dir / f'{self.base_filename}_part{self.json_file_index}.jsonl'
        elif file_format == 'csv' and self.csv_file_index == 1:
            return self.output_dir / f'{self.base_filename}.csv'
        elif file_format == 'csv':
            return self.output_dir / f'{self.base_filename}_part{self.csv_file_index}.csv'
        else:
            # Cho format cố định (không phần)
            return self.output_dir / f'{self.base_filename}.{file_format}'

    def _init_jsonl_file(self):
        """Khởi tạo JSONL, tính tổng size hiện có."""
        self.json_bytes_written = 0
        for file_path in self.output_dir.glob(f'{self.base_filename}*.jsonl'):
            try:
                self.json_bytes_written += file_path.stat().st_size
            except Exception:
                pass
        
        self.json_file_size = 0
        if self.json_file_path.exists():
            self.json_file_size = self.json_file_path.stat().st_size

    def _init_csv_file(self, fieldnames: List[str]):
        """Khởi tạo CSV file với header."""
        if not fieldnames:
            return
        
        self.csv_fieldnames = fieldnames
        try:
            # Mở file ở chế độ append
            file_exists = self.csv_file_path.exists() and self.csv_file_path.stat().st_size > 0
            self.csv_file = open(self.csv_file_path, 'a', newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(
                self.csv_file, 
                fieldnames=fieldnames, 
                extrasaction='ignore'
            )
            
            # Viết header nếu file mới
            if not file_exists:
                self.csv_writer.writeheader()
                self.csv_file.flush()
        except Exception as e:
            print(f"❌ Lỗi tạo CSV file: {e}")

    def _rotate_jsonl_file(self):
        """Chuyển sang file JSONL tiếp theo."""
        self.json_file_index += 1
        self.json_file_path = self._get_filepath('jsonl')
        self.json_file_size = 0

    def _rotate_csv_file(self):
        """Chuyển sang file CSV tiếp theo."""
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
        
        self.csv_file_index += 1
        self.csv_file_path = self._get_filepath('csv')
        self.csv_file_size = 0
        
        if self.csv_fieldnames:
            self._init_csv_file(self.csv_fieldnames)

    def _flush_csv_batch(self):
        """Ghi batch buffer vào CSV."""
        if not self.batch_buffer:
            return
        
        if self.csv_writer is None and self.batch_buffer:
            # Lấy fieldnames từ article đầu tiên
            fieldnames = list(self.batch_buffer[0].keys())
            self._init_csv_file(fieldnames)
        
        if self.csv_writer:
            for article in self.batch_buffer:
                self.csv_writer.writerow(article)
                self.total_articles_to_csv += 1
        
            self.csv_file.flush()
            
            # Cập nhật size
            if self.csv_file_path.exists():
                new_size = self.csv_file_path.stat().st_size
                self.csv_bytes_written += max(new_size - self.csv_file_size, 0)
                self.csv_file_size = new_size
            
            # Kiểm tra rotate
            if self.csv_file_size > self.max_file_size_bytes:
                self._rotate_csv_file()
        
        self.batch_buffer.clear()

    def write_article(self, article: Dict[str, Any], fieldnames: Optional[List[str]] = None):
        """
        Ghi 1 bài báo.
        
        Với format 'json-csv': 
        - Ghi ngay vào JSONL
        - Thêm vào batch buffer, ghi CSV sau khi đủ batch_size
        """
        # Format JSONL hoặc phần JSON của 'json-csv'
        if self.format == 'jsonl' or self.format == 'json-csv':
            line = json.dumps(article, ensure_ascii=False) + '\n'
            line_bytes = len(line.encode('utf-8'))
            
            # Rotate nếu file quá lớn
            if self.json_file_size > 0 and self.json_file_size + line_bytes > self.max_file_size_bytes:
                self._rotate_jsonl_file()
            
            # Ghi vào JSONL
            with open(self.json_file_path, 'a', encoding='utf-8') as f:
                f.write(line)
            
            self.json_file_size += line_bytes
            self.json_bytes_written += line_bytes
        
        # Format CSV hoặc phần CSV của 'json-csv'
        if self.format == 'csv':
            if self.csv_writer is None:
                csv_fields = fieldnames or list(article.keys())
                self._init_csv_file(csv_fields)
            
            if self.csv_writer:
                self.csv_writer.writerow(article)
                self.csv_file.flush()
                new_size = self.csv_file_path.stat().st_size if self.csv_file_path.exists() else 0
                self.csv_bytes_written += max(new_size - self.csv_file_size, 0)
                self.csv_file_size = new_size
                
                if self.csv_file_size > self.max_file_size_bytes:
                    self._rotate_csv_file()
                    if fieldnames:
                        self._init_csv_file(fieldnames)
                
                self.total_articles_to_csv += 1
        
        # Format 'json-csv': Thêm vào batch buffer
        elif self.format == 'json-csv':
            self.batch_buffer.append(article)
            
            # Ghi CSV khi đủ batch_size
            if len(self.batch_buffer) >= self.batch_size:
                self._flush_csv_batch()
        
        self.total_articles += 1

    def flush(self):
        """Ghi batch buffer cuối cùng vào CSV nếu có (dùng trước khi close)."""
        if self.format == 'json-csv':
            self._flush_csv_batch()

    def close(self):
        """Đóng tất cả files và ghi batch cuối."""
        if self.format == 'json-csv':
            self._flush_csv_batch()
        
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        
        self.batch_buffer.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Trả về thống kê ghi."""
        stats = {
            'total_articles': self.total_articles,
            'format': self.format,
        }
        
        if self.format == 'jsonl' or self.format == 'json-csv':
            stats['jsonl_bytes'] = self.json_bytes_written
            stats['jsonl_file_index'] = self.json_file_index
        
        if self.format == 'csv' or self.format == 'json-csv':
            stats['csv_bytes'] = self.csv_bytes_written
            stats['csv_articles_written'] = self.total_articles_to_csv
            stats['csv_file_index'] = self.csv_file_index
            stats['csv_buffer_pending'] = len(self.batch_buffer)
        
        return stats
