# -*- coding: utf-8 -*-
"""
Utilities để lưu và xử lý dữ liệu
"""
import csv
import json
import os
from datetime import datetime
from typing import List, Dict
import pandas as pd


class DataSaver:
    """Class để lưu dữ liệu theo nhiều format"""
    
    def __init__(self, output_dir: str = 'data'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_to_csv(self, data: List[Dict], filename: str = None) -> str:
        """
        Lưu dữ liệu ra file CSV
        
        Args:
            data: Danh sách dictionary chứa dữ liệu
            filename: Tên file (tự động tạo nếu None)
        
        Returns:
            Đường dẫn file đã lưu
        """
        if not data:
            print("⚠️  Không có dữ liệu để lưu")
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'articles_{timestamp}.csv'

        filepath = os.path.join(self.output_dir, filename)

        try:
            # Sử dụng chuẩn cột mong muốn nếu có, ngược lại lấy tất cả key
            DEFAULT_FIELDS = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']

            # Chuẩn hoá từng article sang các trường chuẩn
            normalized = [DataSaver.normalize_article(item, DEFAULT_FIELDS) for item in data]

            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=DEFAULT_FIELDS, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(normalized)

            print(f"✅ Đã lưu {len(normalized)} bài vào: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Lỗi khi lưu CSV: {e}")
            return None
    
    def save_to_json(self, data: List[Dict], filename: str = None, pretty: bool = True) -> str:
        """
        Lưu dữ liệu ra file JSON
        
        Args:
            data: Danh sách dictionary chứa dữ liệu
            filename: Tên file
            pretty: Format JSON đẹp
        
        Returns:
            Đường dẫn file đã lưu
        """
        if not data:
            print("⚠️  Không có dữ liệu để lưu")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'articles_{timestamp}.json'
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(data, f, ensure_ascii=False)
            
            print(f"✅ Đã lưu {len(data)} bài vào: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Lỗi khi lưu JSON: {e}")
            return None
    
    def save_to_jsonl(self, data: List[Dict], filename: str = None) -> str:
        """
        Lưu dữ liệu ra file JSONL (mỗi dòng là một JSON object)
        Format này tốt cho dữ liệu lớn và machine learning
        
        Args:
            data: Danh sách dictionary chứa dữ liệu
            filename: Tên file
        
        Returns:
            Đường dẫn file đã lưu
        """
        if not data:
            print("⚠️  Không có dữ liệu để lưu")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'articles_{timestamp}.jsonl'
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            print(f"✅ Đã lưu {len(data)} bài vào: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Lỗi khi lưu JSONL: {e}")
            return None
    
    def append_to_csv(self, data: List[Dict], filename: str):
        """Thêm dữ liệu vào file CSV đã có"""
        filepath = os.path.join(self.output_dir, filename)
        
        if not os.path.exists(filepath):
            return self.save_to_csv(data, filename)
        
        try:
            # Đọc file hiện có để lấy fieldnames
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
            
            # Thêm dữ liệu mới (chuyển về cột chuẩn trước khi append)
            DEFAULT_FIELDS = ['URL', 'Title', 'Summary', 'Contents', 'Date', 'Author(s)', 'Category', 'Tags']
            normalized = [DataSaver.normalize_article(item, DEFAULT_FIELDS) for item in data]
            with open(filepath, 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(normalized)
            
            print(f"✅ Đã thêm {len(data)} bài vào: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Lỗi khi append CSV: {e}")
            return None

    @staticmethod
    def normalize_article(item: Dict, fields: List[str]) -> Dict:
        """
        Chuyển một record bài viết (với nhiều dạng key khác nhau) sang dict có các key chuẩn.

        Quy tắc map:
        - URL: 'link' or 'url'
        - Title: 'tieu_de' or 'title' or 'headline'
        - Summary: 'tom_tat' or 'summary' or first 200 chars of content
        - Contents: 'noi_dung' or 'content' or 'contents' or 'full_text'
        - Date: 'ngay' or 'date' or 'published'
        - Author(s): 'tac_gia' or 'author' or 'authors'
        - Category: 'chu_de' or 'category'
        """
        # Hàm check mảng key: Do các nguồn khác nhau trả data field khác nhau (thằng xài url, thằng xài link)
        def get_first(keys):
            for k in keys:
                if k in item and item.get(k):
                    return item.get(k)
            return ''

        # (Normalizing) Gom nhóm các thể loại thuộc tính lung tung về 1 Key chuẩn để xuất file CSV
        url = get_first(['link', 'url'])
        title = get_first(['tieu_de', 'title', 'headline'])
        contents = get_first(['noi_dung', 'content', 'contents', 'full_text'])
        
        # Riêng thuộc tính Tóm tắt, nếu bài ko có sẵn, mạnh dạn cắt lấu 200 ký tự content đầu tiền đắp vào
        summary = get_first(['tom_tat', 'summary']) or (contents[:200] if contents else '')
        date = get_first(['ngay', 'date', 'published'])
        authors = get_first(['tac_gia', 'author', 'authors'])
        category = get_first(['chu_de', 'category'])
        tags = get_first(['tags', 'keywords', 'tu_khoa'])

        # đảm bảo chuỗi
        def norm_str(v):
            if v is None:
                return ''
            if isinstance(v, list):
                s = '; '.join(map(str, v))
            else:
                s = str(v)
            # Loại bỏ xuống dòng và khoảng trắng dư
            return ' '.join(s.split())

        normalized = {
            'URL': norm_str(url),
            'Title': norm_str(title),
            'Summary': norm_str(summary),
            'Contents': norm_str(contents),
            'Date': norm_str(date),
            'Author(s)': norm_str(authors),
            'Category': norm_str(category),
            'Tags': norm_str(tags),
        }
        return normalized


class DataCleaner:
    """Class để làm sạch và xử lý dữ liệu"""
    
    @staticmethod
    def remove_duplicates(data: List[Dict], key: str = 'noi_dung') -> List[Dict]:
        """
        Loại bỏ bài viết trùng lặp dựa trên một key
        
        Args:
            data: Danh sách dữ liệu
            key: Key để kiểm tra trùng lặp
        
        Returns:
            Danh sách đã loại bỏ trùng lặp
        """
        seen = set()
        unique_data = []
        
        for item in data:
            identifier = item.get(key)
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique_data.append(item)
        
        removed = len(data) - len(unique_data)
        if removed > 0:
            print(f"🧹 Đã loại bỏ {removed} bài trùng lặp")
        
        return unique_data
    
    @staticmethod
    def filter_by_length(data: List[Dict], min_length: int = 100, text_field: str = 'noi_dung') -> List[Dict]:
        """
        Lọc bài viết theo số từ tối thiểu
        
        Args:
            data: Danh sách dữ liệu
            min_length: Số từ tối thiểu (mặc định: 100 từ)
            text_field: Tên field chứa nội dung
        
        Returns:
            Danh sách đã lọc
        """
        filtered_data = [
            item for item in data 
            if item.get(text_field) and len(item[text_field].split()) >= min_length
        ]
        
        removed = len(data) - len(filtered_data)
        if removed > 0:
            print(f"🧹 Đã loại bỏ {removed} bài quá ngắn")
        
        return filtered_data
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Làm sạch text: loại bỏ ký tự đặc biệt, khoảng trắng thừa
        
        Args:
            text: Text cần làm sạch
        
        Returns:
            Text đã làm sạch
        """
        if not text:
            return ''
        
        # Loại bỏ khoảng trắng thừa
        text = ' '.join(text.split())
        
        # Loại bỏ các ký tự điều khiển
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        
        return text.strip()
    
    @staticmethod
    def clean_dataset(data: List[Dict]) -> List[Dict]:
        """
        Làm sạch toàn bộ dataset
        
        Args:
            data: Danh sách dữ liệu
        
        Returns:
            Danh sách đã làm sạch
        """
        print("🧹 Bắt đầu làm sạch dữ liệu...")
        
        # Loại bỏ trùng lặp
        data = DataCleaner.remove_duplicates(data)
        
        # Lọc theo độ dài
        data = DataCleaner.filter_by_length(data)
        
        # Làm sạch text
        for item in data:
            if 'noi_dung' in item:
                item['noi_dung'] = DataCleaner.clean_text(item['noi_dung'])
        
        print(f"✅ Hoàn thành làm sạch. Còn lại: {len(data)} bài")
        return data


class DataAnalyzer:
    """Class để phân tích dữ liệu"""
    
    @staticmethod
    def get_statistics(data: List[Dict]) -> Dict:
        """
        Lấy thống kê cơ bản về dữ liệu
        
        Args:
            data: Danh sách dữ liệu
        
        Returns:
            Dictionary chứa thống kê
        """
        if not data:
            return {}
        
        stats = {
            'total_articles': len(data),
            'categories': {},
            'avg_length': 0,
            'avg_words': 0,
            'min_length': float('inf'),
            'max_length': 0,
        }
        
        total_length = 0
        total_words = 0
        
        for item in data:
            # Thống kê theo chuyên mục
            category = item.get('chu_de', 'Unknown')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            text_length = len(item.get('noi_dung', ''))
            word_count = len(item.get('noi_dung', '').split())
            total_length += text_length
            total_words += word_count
            stats['min_length'] = min(stats['min_length'], text_length)
            stats['max_length'] = max(stats['max_length'], text_length)
        
        stats['avg_length'] = total_length / len(data) if data else 0
        stats['avg_words'] = total_words / len(data) if data else 0
        stats['avg_length'] = total_length / len(data) if data else 0
        
        return stats
    
    @staticmethod
    def print_statistics(stats: Dict):
        """In thống kê ra console"""
        print("\n" + "="*60)
        print("📊 THỐNG KÊ DỮ LIỆU")
        print("="*60)
        
        print(f"\n📝 Tổng số bài: {stats['total_articles']}")
        
        print(f"\n📂 Phân bố theo chủ đề:")
        print(f"\n📏 Độ dài nội dung:")
        print(f"  • Trung bình: {stats['avg_words']:.0f} từ ({stats['avg_length']:.0f} ký tự)")
        print(f"  • Ngắn nhất: {stats['min_length']} ký tự")
        print(f"  • Dài nhất: {stats['max_length']} ký tự")
        print(f"  • Trung bình: {stats['avg_length']:.0f} ký tự")
        print(f"  • Ngắn nhất: {stats['min_length']} ký tự")
        print(f"  • Dài nhất: {stats['max_length']} ký tự")
        
        print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    # Test
    test_data = [
        {'chu_de': 'thoi-su', 'noi_dung': 'Test 1. ' + 'A' * 200},
        {'chu_de': 'kinh-doanh', 'noi_dung': 'Test 2. ' + 'B' * 300},
        {'chu_de': 'thoi-su', 'noi_dung': 'Test 1. ' + 'A' * 200},  # Duplicate
    ]
    
    # Test cleaner
    cleaner = DataCleaner()
    cleaned = cleaner.clean_dataset(test_data)
    
    # Test analyzer
    analyzer = DataAnalyzer()
    stats = analyzer.get_statistics(cleaned)
    analyzer.print_statistics(stats)
    
    # Test saver
    saver = DataSaver('test_output')
    saver.save_to_csv(cleaned, 'test.csv')
    saver.save_to_json(cleaned, 'test.json')
