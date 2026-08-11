# -*- coding: utf-8 -*-
"""从已修正的 articles.json 重新生成全部分类 Markdown，保证日期格式一致"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrape_activebeat as sa

data = json.load(open(os.path.join(sa.OUT_DIR, "articles.json"), encoding="utf-8"))
os.makedirs(sa.MD_DIR, exist_ok=True)
for cat in data["categories"]:
    md = sa.to_markdown(cat, cat["articles"])
    with open(os.path.join(sa.MD_DIR, f"{cat['slug']}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(f"重写 {cat['slug']}.md ({len(cat['articles'])} 篇)")
