# -*- coding: utf-8 -*-
"""
从 scraped/articles.json 生成：
  1) 前端数据文件 js/articles-data.js（列表页用，不含正文）
  2) 每篇文章的独立静态页 articles/<id>-<slug>.html（含完整正文）
封面使用 CSS 渐变（分类基准色相 + id 微调 + 角度），不依赖外部图片。
"""
import html as html_lib
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime

import site_config

ROOT = os.path.dirname(os.path.abspath(__file__))
# 核心数据/看板目录（与公开网站彻底隔离，路径见 site_config.py）
JSON_PATH = site_config.ARTICLES_JSON
OUT_PATH = os.path.join(site_config.JS_DIR, "articles-data.js")
ARTICLES_DIR = site_config.ARTICLES_DIR
IMAGES_DIR = site_config.IMAGES_DIR

# slug -> (分类显示名, 图标)
CATEGORY_META = {
    "health-news": ("Health News", "📰"),
    "diet-nutrition": ("Diet & Nutrition", "🍎"),
    "fitness": ("Fitness", "💪"),
    "your-health-men": ("Men", "👨"),
    "your-health-women": ("Women", "👩"),
    "your-health-children": ("Children", "👶"),
    "your-health-senior": ("Senior", "👵"),
    "interest-diabetes": ("Diabetes", "🩸"),
    "interest-heart-health": ("Heart Health", "❤️"),
    "interest-mental-health": ("Mental Health", "🧠"),
    "travel": ("Travel", "✈️"),
    "automotive": ("Automotive", "🚗"),
    "personal-finance": ("Finance", "💰"),
    "interest-home-garden": ("Home & Garden", "🏡"),
    "interest-technology": ("Technology", "💻"),
}

# 各分类封面渐变的基准色相（hue）
CATEGORY_HUES = {
    "health-news": 205,
    "diet-nutrition": 30,
    "fitness": 262,
    "your-health-men": 214,
    "your-health-women": 330,
    "your-health-children": 45,
    "your-health-senior": 275,
    "interest-diabetes": 0,
    "interest-heart-health": 348,
    "interest-mental-health": 185,
    "travel": 150,
    "automotive": 220,
    "personal-finance": 100,
    "interest-home-garden": 82,
    "interest-technology": 192,
}


def make_cover(cat_slug, art_id):
    """按分类基准色相 + 文章 id 生成唯一的 CSS 渐变封面（色相 + 角度双维度变化）"""
    base = CATEGORY_HUES.get(cat_slug, 210)
    hue = (base + art_id % 24 - 12) % 360
    angle = (art_id * 137) % 360
    return f"linear-gradient({angle}deg, hsl({hue}, 62%, 56%), hsl({(hue + 40) % 360}, 70%, 42%))"


def parse_date(s):
    """尝试把日期字符串转为 (sortable int, 展示字符串)；失败返回 (0, '')"""
    if not s:
        return 0, ""
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.strftime("%Y%m%d"), d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return 0, s


def make_excerpt(blocks, limit=140):
    """取正文第一个段落的文本作为摘要"""
    text = ""
    for b in blocks:
        if b["type"] == "p":
            text = re.sub(r"\s+", " ", b["text"]).strip()
            break
    if not text:
        text = re.sub(r"\s+", " ", " ".join(b["text"] for b in blocks)).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:70].strip("-") or "article"


def make_page_path(art_id, title, url):
    """文章页文件名：基于标题 slug + URL 哈希，保证稳定（新增/删除文章不影响其他页面名）"""
    h = hashlib.md5((url or title).encode("utf-8")).hexdigest()[:6]
    return f"articles/{slugify(title)}-{h}.html"


def blocks_to_html(blocks):
    """把结构化正文块转为 HTML；连续的 li 合并为 <ul>"""
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        if b["type"] == "li":
            items = []
            while i < len(blocks) and blocks[i]["type"] == "li":
                items.append(f"<li>{html_lib.escape(blocks[i]['text'])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        tag = {"p": "p", "h2": "h2", "h3": "h3", "h4": "h4", "blockquote": "blockquote"}.get(b["type"], "p")
        out.append(f"<{tag}>{html_lib.escape(b['text'])}</{tag}>")
        i += 1
    return "\n".join(out)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{excerpt}">
  <title>{title} - ChoiceGuide</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Covered+By+Your+Grace&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../css/style.css">
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a href="../index.html" class="logo">
        <span class="logo-mark">✓</span>
        <span class="logo-text">ChoiceGuide</span>
      </a>
      <nav class="main-nav">
        <a href="../index.html" class="nav-link">Home</a>
        <a href="../index.html#categories" class="nav-link">Categories</a>
        <a href="../index.html#latest" class="nav-link">Latest</a>
        <a href="../index.html#about" class="nav-link">About</a>
      </nav>
    </div>
  </header>

  <main class="container">
    <article class="article-detail">
      <nav class="article-breadcrumb"><a href="../index.html">Home</a> / <span>{category}</span></nav>
      <h1 class="article-detail-title">{title}</h1>
      <div class="article-detail-meta">
        <span class="card-tag">{category}</span>
        <span>Published: {date}</span>
        <span>By {authors}</span>
        <span>{read_time}</span>
        <span>{word_count} words</span>
      </div>
{image_html}
      <div class="article-detail-content">
{content}
      </div>
      <div class="article-author-bio">
        <span class="article-author-bio__avatar">👤</span>
        <div class="article-author-bio__info">
          <p class="article-author-bio__name">By {authors}</p>
          <p class="article-author-bio__desc">Written and reviewed by the ChoiceGuide health content team.</p>
        </div>
      </div>
      <p class="article-source">Source: <a href="{url}" target="_blank" rel="nofollow noopener">{url}</a></p>
      <p class="article-back"><a href="../index.html">&larr; Back to home</a></p>
    </article>
  </main>

  <footer class="site-footer">
    <div class="container footer-inner">
      <div class="footer-brand">
        <span class="logo-mark">✓</span>
        <span class="logo-text">ChoiceGuide</span>
        <p class="footer-desc">Science-based health. Your guide to health and healthy living.</p>
      </div>
      <div class="footer-links">
        <a href="../index.html#featured">Featured</a>
        <a href="../index.html#categories">Categories</a>
        <a href="../index.html#latest">Latest</a>
        <a href="../index.html#about">About</a>
      </div>
      <p class="copyright">© 2026 choiceguide.xyz · Content is for reference only, not medical advice.</p>
    </div>
  </footer>
  <script src="../js/track.js"></script>
</body>
</html>
"""


def render_article_page(art):
    blocks_html = blocks_to_html(art["blocks"])
    content = "\n".join("        " + line for line in blocks_html.splitlines())
    image_html = (
        f'      <img class="article-detail__image" src="../{art["image"]}" '
        f'alt="{html_lib.escape(art["title"])}" loading="lazy">\n'
        if art.get("image")
        else ""
    )
    return PAGE_TEMPLATE.format(
        title=html_lib.escape(art["title"]),
        excerpt=html_lib.escape(art["excerpt"][:150]),
        category=html_lib.escape(art["category"]),
        date=html_lib.escape(art["date"]),
        authors=html_lib.escape(", ".join(art["authors"]) if art["authors"] else "Unknown"),
        read_time=html_lib.escape(art["read_time"]),
        word_count=art["word_count"],
        content=content,
        image_html=image_html,
        url=html_lib.escape(art["url"]),
    )


def generate_article_pages(page_articles):
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    for art in page_articles:
        path = os.path.join(ARTICLES_DIR, art["page"].split("/", 1)[1])
        with open(path, "w", encoding="utf-8") as f:
            f.write(render_article_page(art))
    print(f"文章页: {len(page_articles)} 个 -> {ARTICLES_DIR}")


def cleanup_orphans(used_names, used_image_names):
    """删除去重后不再被引用的文章页与配图，避免陈旧文件残留"""
    removed = 0
    # 文章页：按页面名清理
    if os.path.isdir(ARTICLES_DIR):
        for fn in os.listdir(ARTICLES_DIR):
            stem = fn.rsplit(".", 1)[0]
            if stem not in used_names:
                os.remove(os.path.join(ARTICLES_DIR, fn))
                removed += 1
    # 配图：按实际被引用的图片名清理
    if os.path.isdir(IMAGES_DIR):
        for fn in os.listdir(IMAGES_DIR):
            stem = fn.rsplit(".", 1)[0]
            if stem not in used_image_names:
                os.remove(os.path.join(IMAGES_DIR, fn))
                removed += 1
    return removed


# 爬取数据看板（内部核心数据，与公开网站分离；路径见 site_config.py）
HISTORY_PATH = site_config.HISTORY_PATH
DASHBOARD_OUT = site_config.DASHBOARD_OUT


def update_history(cat_counts, image_count):
    """按天记录一次爬取快照（同一天只保留最新一次），并计算当日新增量"""
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    hist = []
    if os.path.exists(HISTORY_PATH):
        try:
            hist = json.load(open(HISTORY_PATH, encoding="utf-8"))
        except Exception:
            hist = []
    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(cat_counts.values())
    prev = None
    for e in hist:
        if e.get("date") != today and (prev is None or e["date"] > prev["date"]):
            prev = e
    entry = {
        "date": today,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "articles": total,
        "images": image_count,
        "newArticles": max(0, total - (prev["articles"] if prev else 0)),
        "newImages": max(0, image_count - (prev["images"] if prev else 0)),
        "categories": cat_counts,
    }
    hist = [e for e in hist if e.get("date") != today]
    hist.append(entry)
    hist.sort(key=lambda e: e["date"])
    json.dump(hist, open(HISTORY_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return hist


def generate_dashboard_data(categories, articles, pub_years):
    """生成看板数据 js/dashboard-data.js：汇总卡片 + 每日爬取历史 + 分类分布 + 发布时间分布"""
    os.makedirs(os.path.dirname(DASHBOARD_OUT), exist_ok=True)
    cat_counts = Counter(a["category"] for a in articles)
    image_count = sum(1 for a in articles if a.get("image"))
    hist = update_history(dict(cat_counts), image_count)
    data = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "totalArticles": len(articles),
        "imageCount": image_count,
        "categoryCount": sum(1 for c in categories if c["name"] != "All"),
        "categories": [
            {"name": c["name"], "icon": c["icon"], "count": cat_counts.get(c["name"], 0)}
            for c in categories
        ],
        "history": hist,
        "pubYears": {str(k): v for k, v in sorted(pub_years.items())},
    }
    js = "/* 由 build_site_data.py 自动生成，请勿手动编辑 */\n"
    js += "window.DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    with open(DASHBOARD_OUT, "w", encoding="utf-8") as f:
        f.write(js)
    return hist


def build():
    data = json.load(open(JSON_PATH, encoding="utf-8"))

    categories, articles, page_articles, art_id = [], [], [], 1
    seen_urls, used_names, used_image_names = set(), set(), set()
    skipped_cats = []
    pub_years = Counter()
    for cat in data["categories"]:
        name, icon = CATEGORY_META.get(cat["slug"], (cat["name"], "📄"))
        # 全局按 URL 去重：同一篇文章只保留在第一次出现的分类下
        cat_articles = []
        for a in cat["articles"]:
            if a["url"] in seen_urls:
                continue
            seen_urls.add(a["url"])
            cat_articles.append(a)
        if not cat_articles:
            skipped_cats.append(name)
            continue
        categories.append({"name": name, "icon": icon})
        for a in cat_articles:
            sort_key, show_date = parse_date(a.get("published") or a.get("date_raw"))
            if sort_key:
                pub_years[sort_key[:4]] += 1
            page = make_page_path(art_id, a["title"], a["url"])
            used_names.add(page.rsplit("/", 1)[1].rsplit(".", 1)[0])
            if a.get("image"):
                used_image_names.add(os.path.basename(a["image"]).rsplit(".", 1)[0])
            articles.append({
                "id": art_id,
                "title": a["title"],
                "category": name,
                "excerpt": make_excerpt(a.get("content", [])),
                "date": show_date or "Unknown date",
                "_sort": sort_key,
                "authors": a.get("authors", []),
                "read_time": a.get("read_time", ""),
                "word_count": a.get("word_count", 0),
                "url": a["url"],
                "page": page,
                "image": a.get("image", ""),
                "featured": False,
                "cover": make_cover(cat["slug"], art_id),
            })
            page_articles.append({
                "id": art_id,
                "title": a["title"],
                "category": name,
                "excerpt": make_excerpt(a.get("content", [])),
                "date": show_date or "Unknown date",
                "authors": a.get("authors", []),
                "read_time": a.get("read_time", ""),
                "word_count": a.get("word_count", 0),
                "url": a["url"],
                "page": page,
                "image": a.get("image", ""),
                "blocks": a.get("content", []),
            })
            art_id += 1

    # 热门精选：按日期取最新的 3 篇
    by_date = sorted((a for a in articles if a["_sort"]), key=lambda x: x["_sort"], reverse=True)
    for a in by_date[:3]:
        a["featured"] = True

    for a in articles:
        del a["_sort"]

    categories.append({"name": "All", "icon": "✨"})

    out = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": data.get("source", ""),
        "categories": categories,
        "articles": articles,
    }
    js = "/* 由 build_site_data.py 自动生成，请勿手动编辑 */\n"
    js += "window.SCRAPED_DATA = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n"
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(js)

    generate_article_pages(page_articles)
    removed = cleanup_orphans(used_names, used_image_names)
    hist = generate_dashboard_data(categories, articles, pub_years)

    print(f"生成 {OUT_PATH}")
    print(f"  分类: {len(categories)} 个（含\"All\"；已跳过无独立内容的分类: {', '.join(skipped_cats) if skipped_cats else '无'}）")
    print(f"  文章: {len(articles)} 篇（去重后唯一，featured={sum(1 for a in articles if a['featured'])}）")
    print(f"  清理陈旧页面/图片: {removed} 个")
    print(f"  看板历史记录: {len(hist)} 天 -> {DASHBOARD_OUT}")
    sample = next(a for a in articles if a["id"] == 1)
    print("  样例:", sample["title"], "|", sample["category"], "|", sample["date"], "|", sample["page"])


if __name__ == "__main__":
    build()
