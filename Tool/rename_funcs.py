import os
import re

replacements = {
    r'\bcrawl_sources\b': 'cao_cac_nguon_bao',
    r'\bcrawl_source\b': 'cao_mot_nguon_bao',
    r'\bcrawl_category\b': 'cao_chuyen_muc',
    r'\bget_article_links\b': 'lay_link_bai_viet',
    r'\bextract_article\b': 'trich_xuat_bai_viet',
    r'\bcrawl_one\b': 'cao_thu_mot_bai'
}

for root, dirs, files in os.walk(r'F:\tool\Tool'):
    if 'venv' in root or '.git' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.md'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            orig_content = content
            for pattern, repl in replacements.items():
                content = re.sub(pattern, repl, content)
            
            if content != orig_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filepath}")
