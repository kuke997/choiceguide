# -*- coding: utf-8 -*-
"""
activebeat.com 小范围内容爬取脚本（仅个人学习参考用，请遵守目标站服务条款）

范围：15 个分类 × 前 10 篇文章，不爬视频内容。
输出：
  - scraped/articles.json        结构化数据（全部文章）
  - scraped/markdown/<slug>.md   每个分类一份可读 Markdown
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import site_config

BASE = "https://activebeat.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 30
MAX_ARTICLES = 10          # 每分类前 10 篇
MAX_PAGES = 6              # 列表页最多翻页数（防止死循环）
DELAY = 0.6                # 请求间隔（秒），避免给目标站造成压力
RETRIES = 3

# 核心数据目录（与公开网站彻底隔离，不随站点部署；路径见 site_config.py）
OUT_DIR = site_config.SCRAPED_DIR
MD_DIR = site_config.MARKDOWN_DIR

# 分类清单：name = 分类显示名, slug = 输出文件名, urls = 列表页（可多个来源合并）
CATEGORIES = [
    {"name": "Health News 健康资讯", "slug": "health-news", "url": f"{BASE}/health-news/", "urls": [f"{BASE}/health-news/"]},
    {"name": "Diet & Nutrition 饮食与营养", "slug": "diet-nutrition", "url": f"{BASE}/diet-nutrition/", "urls": [f"{BASE}/diet-nutrition/"]},
    {"name": "Fitness 健身", "slug": "fitness", "url": f"{BASE}/fitness/", "urls": [f"{BASE}/fitness/"]},
    {"name": "Your Health - Men 男性健康", "slug": "your-health-men", "url": f"{BASE}/your-health/men/", "urls": [f"{BASE}/your-health/men/"]},
    {"name": "Your Health - Women 女性健康", "slug": "your-health-women", "url": f"{BASE}/your-health/women/", "urls": [f"{BASE}/your-health/women/"]},
    {"name": "Your Health - Children 儿童健康", "slug": "your-health-children", "url": f"{BASE}/your-health/children/", "urls": [f"{BASE}/your-health/children/"]},
    {"name": "Your Health - Senior 老年健康", "slug": "your-health-senior", "url": f"{BASE}/your-health/senior/", "urls": [f"{BASE}/your-health/senior/"]},
    {"name": "Interest - Diabetes 糖尿病专题", "slug": "interest-diabetes", "url": f"{BASE}/interest/diabetes/", "urls": [f"{BASE}/interest/diabetes/"]},
    {"name": "Interest - Heart Health 心脏健康专题", "slug": "interest-heart-health", "url": f"{BASE}/interest/heart-health/", "urls": [f"{BASE}/interest/heart-health/"]},
    {"name": "Interest - Mental Health 心理健康专题", "slug": "interest-mental-health", "url": f"{BASE}/interest/mental-health/", "urls": [f"{BASE}/interest/mental-health/"]},
    {"name": "Travel 旅游", "slug": "travel", "url": f"{BASE}/travel/", "urls": [f"{BASE}/travel/"]},
    {"name": "Automotive 汽车", "slug": "automotive", "url": f"{BASE}/automotive/", "urls": [f"{BASE}/automotive/"]},
    {"name": "Personal Finance 理财", "slug": "personal-finance", "url": f"{BASE}/personal-finance/", "urls": [f"{BASE}/personal-finance/"]},
    {"name": "Interest - Home & Garden 家居园艺", "slug": "interest-home-garden", "url": f"{BASE}/interest/home/",
     "urls": [f"{BASE}/interest/home/", f"{BASE}/interest/gardening/", f"{BASE}/interest/healthy-home/",
              f"{BASE}/interest/diy/", f"{BASE}/interest/eco/"]},
    {"name": "Interest - Technology 科技", "slug": "interest-technology", "url": f"{BASE}/interest/technology/", "urls": [f"{BASE}/interest/technology/"]},
]

VIDEO_MARKERS = ("/videos/", "/video/", "/parenting/video/")
session = requests.Session()
session.headers.update(HEADERS)


def fetch(url, max_retry=RETRIES):
    """带重试的 GET 请求"""
    for i in range(max_retry):
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            print(f"    [warn] {url} -> HTTP {r.status_code}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"    [warn] {url} -> {e}", file=sys.stderr)
        time.sleep(DELAY * 3)
    return None


def list_article_urls(cat):
    """从分类的多个列表页（含翻页）收集最多 MAX_ARTICLES 篇文章 URL，跳过视频"""
    urls, seen = [], set()
    for cat_url in cat["urls"]:
        if len(urls) >= MAX_ARTICLES:
            break
        page = 1
        while len(urls) < MAX_ARTICLES and page <= MAX_PAGES:
            url = cat_url if page == 1 else f"{cat_url.rstrip('/')}/page/{page}/"
            r = fetch(url)
            if r is None:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.select("article.post-module__item")
            if not cards:
                # 该页没有卡片（如索引页/最后一页），直接退出
                break
            for card in cards:
                if len(urls) >= MAX_ARTICLES:
                    break
                a = card.select_one("a.post-module__thumb-link") or card.find("a", href=True)
                if not a:
                    continue
                href = urljoin(BASE, a["href"])
                if href in seen:
                    continue
                seen.add(href)
                # 排除作者页/分类导航等非文章链接
                if "/author/" in href or href.rstrip("/").endswith(("/your-health", "/fitness", "/diet-nutrition",
                                                                    "/health-news", "/travel", "/automotive",
                                                                    "/personal-finance", "/food", "/lifestyle")):
                    continue
                if any(m in href for m in VIDEO_MARKERS):
                    continue
                urls.append(href)
            page += 1
            time.sleep(DELAY)
    return urls


def parse_article(url):
    """解析单篇文章页，返回结构化字典；是视频页则返回 None"""
    r = fetch(url)
    if r is None:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.select_one("main") or soup
    title_node = main.select_one("h1.post-title") or soup.select_one("h1")
    title = title_node.get_text(strip=True) if title_node else ""

    # 视频检测：正文区有 youtube iframe / video 标签即视为视频文章
    if soup.select_one("iframe[src*='youtube'], iframe[src*='youtu.be'], video, .wp-block-embed-youtube"):
        return None

    # 日期
    date_str, date_iso = "", ""
    time_node = main.select_one("time.post-date, time.entry-date, time")
    if time_node:
        date_str = time_node.get_text(strip=True).replace("Published on ", "").replace("Published:", "").strip().rstrip(".")
        try:
            date_iso = datetime.strptime(date_str, "%B %d, %Y").date().isoformat()
        except ValueError:
            try:
                date_iso = datetime.strptime(date_str, "%b %d, %Y").date().isoformat()
            except ValueError:
                date_iso = date_str
                date_str = date_iso

    # 作者
    authors = []
    for a in main.select(".author-info a[href*='/author/']"):
        name = a.get_text(strip=True)
        if name and name not in authors:
            authors.append(name)

    # 阅读时长
    read_time = ""
    rt = main.select_one("p.post-read-time, .read-time")
    if rt:
        read_time = rt.get_text(strip=True)

    # 面包屑分类
    breadcrumb = ""
    bc = main.select_one("nav.breadcrumb")
    if bc:
        breadcrumb = " > ".join(x.get_text(strip=True) for x in bc.select("a, span") if x.get_text(strip=True))

    # 正文：按顺序提取 article.content 下的段落/标题/列表（保留元素类型）
    content_node = main.select_one("article.content, .entry-content, .post-content")
    if content_node is None:
        content_node = main
    blocks = []
    for el in content_node.find_all(["p", "h2", "h3", "h4", "li", "blockquote"], recursive=True):
        # 跳过隐藏在 script/style/iframe 内的文本
        if el.find_parent(["script", "style", "iframe"]):
            continue
        text = el.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        # 过滤导航性/装饰性短文本
        if el.name == "p" and (len(text) < 25 or text in ("Read More", "Share this article")):
            continue
        if text.startswith(("Share this", "Facebook", "Twitter", "Pinterest", "Table of Contents")):
            continue
        blocks.append({"type": el.name, "text": text})

    word_count = sum(len(b["text"].split()) for b in blocks)

    return {
        "title": title,
        "url": url,
        "published": date_iso,
        "date_raw": date_str,
        "authors": authors,
        "read_time": read_time,
        "breadcrumb": breadcrumb,
        "word_count": word_count,
        "block_count": len(blocks),
        "content": blocks,
    }


def to_markdown(cat, articles):
    lines = [f"# {cat['name']}", "", f"> 来源列表页：{cat['url']}", f"> 共 {len(articles)} 篇", "", "---", ""]
    for i, a in enumerate(articles, 1):
        lines += [
            f"## {i}. {a['title']}", "",
            f"- 链接：{a['url']}",
            f"- 发布时间：{a['published'] or a['date_raw']}",
            f"- 作者：{', '.join(a['authors']) if a['authors'] else '未知'}",
            f"- 阅读时长：{a['read_time']}",
            f"- 字数：{a['word_count']}",
            f"- 分类路径：{a['breadcrumb']}",
            "", "### 正文", "",
        ]
        for b in a["content"]:
            if b["type"] == "h2":
                lines += ["", f"#### {b['text']}", ""]
            elif b["type"] == "h3":
                lines += ["", f"##### {b['text']}", ""]
            elif b["type"] == "h4":
                lines += ["", f"**{b['text']}**", ""]
            elif b["type"] == "li":
                lines.append(f"- {b['text']}")
            else:
                lines.append(b["text"])
                lines.append("")
        lines += ["---", ""]
    return "\n".join(lines)


def load_existing():
    """读取已有爬取数据（增量爬取基础）"""
    if not os.path.exists(site_config.ARTICLES_JSON):
        return {"generated_at": "", "source": BASE, "categories": []}
    try:
        with open(site_config.ARTICLES_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"generated_at": "", "source": BASE, "categories": []}


def main():
    args = sys.argv[1:]
    full = "--full" in args            # --full：强制全量重抓；默认增量（只抓新文章）
    only = [a for a in args if a != "--full"]

    existing = load_existing()
    known = {a["url"] for cat in existing["categories"] for a in cat["articles"]}
    by_slug = {c["slug"]: c for c in existing["categories"]}
    stats = []
    new_total = 0

    categories = [c for c in CATEGORIES if not only or c["slug"] in only]
    for cat in categories:
        print(f"[1/3] 列表：{cat['name']} <- {cat['url']}", flush=True)
        urls = list_article_urls(cat)
        new_urls = urls if full else [u for u in urls if u not in known]
        print(f"       候选 {len(urls)} 篇，其中新增 {len(new_urls)} 篇", flush=True)
        fetched = []
        for j, u in enumerate(new_urls, 1):
            print(f"[2/3] 抓取新文章 {j}/{len(new_urls)}: {u}", flush=True)
            art = parse_article(u)
            if art is None:
                print("       [skip] 视频文章，跳过", flush=True)
                continue
            fetched.append(art)
            known.add(u)
            time.sleep(DELAY)

        # 合并到已有分类（按 URL 去重）
        old = by_slug.get(cat["slug"])
        merged = list(old["articles"]) if old else []
        have = {a["url"] for a in merged if a.get("url")}
        for a in fetched:
            if a["url"] not in have:
                merged.append(a)
                have.add(a["url"])
        if old is None:
            cat_data = {"name": cat["name"], "slug": cat["slug"], "url": cat["url"],
                        "article_count": len(merged), "articles": merged}
            by_slug[cat["slug"]] = cat_data
            existing["categories"].append(cat_data)
        else:
            old["articles"] = merged
            old["article_count"] = len(merged)

        if fetched:
            with open(os.path.join(MD_DIR, f"{cat['slug']}.md"), "w", encoding="utf-8") as f:
                f.write(to_markdown(cat, merged))
        new_total += len(fetched)
        stats.append((cat["name"], len(fetched)))
        time.sleep(DELAY)

    changed = new_total > 0 or not existing["categories"]
    if changed:
        existing["generated_at"] = datetime.now().isoformat(timespec="seconds")
        existing["source"] = BASE
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(site_config.ARTICLES_JSON, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    else:
        print("无新增内容，跳过数据文件写入")

    print("\n===== 汇总 =====")
    for name, n in stats:
        print(f"  {name}: 新增 {n} 篇")
    print(f"  本次新增合计: {new_total} 篇；当前唯一 URL 总量: {len(known)}")
    print("输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
