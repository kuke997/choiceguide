# -*- coding: utf-8 -*-
"""
为每篇文章下载参考站配图（cdn2 缩略图，约几十 KB/张），保存到 images/，
并把相对路径写回 scraped/articles.json 的 image 字段。

注意：图片版权归原站所有，仅用于本项目的参考/学习用途。
"""
import json
import os
import re
import sys
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

import site_config

ROOT = os.path.dirname(os.path.abspath(__file__))
# 核心数据目录（与公开网站彻底隔离）；配图仍输出到网站 images/ 目录供前端使用
JSON_PATH = site_config.ARTICLES_JSON
IMAGES_DIR = site_config.IMAGES_DIR

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://activebeat.com/",
}
DELAY = 0.5
RETRIES = 3

session = requests.Session()
session.headers.update(HEADERS)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:70].strip("-") or "article"


def page_name(art_id, title):
    return f"{art_id}-{slugify(title)}"


def fetch(url, timeout=40):
    for i in range(RETRIES):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(DELAY * 3)
    return None


def extract_image_url(html):
    """从文章页 HTML 提取配图 URL：优先 featured-image 的 img src，其次 og:image"""
    soup = BeautifulSoup(html, "html.parser")
    img = soup.select_one(".featured-image img, main .featured-image img")
    if img:
        src = img.get("src") or img.get("data-src")
        if src and src.startswith("http"):
            return src
    og = soup.find("meta", property="og:image")
    if og and og.get("content", "").startswith("http"):
        return og["content"]
    return None


def download_image(url, path):
    r = fetch(url)
    if r is None:
        return False
    if not r.content or len(r.content) < 1000:
        return False
    ctype = (r.headers.get("Content-Type") or "").lower()
    ext = "png" if "png" in ctype else ("webp" if "webp" in ctype else "jpg")
    path = path.rsplit(".", 1)[0] + "." + ext
    with open(path, "wb") as f:
        f.write(r.content)
    return True


def main():
    data = json.load(open(JSON_PATH, encoding="utf-8"))
    os.makedirs(IMAGES_DIR, exist_ok=True)

    art_id = 0
    ok, fail, skipped = 0, 0, 0
    for cat in data["categories"]:
        for a in cat["articles"]:
            art_id += 1
            if a.get("image"):
                skipped += 1
                continue
            base = os.path.join(IMAGES_DIR, page_name(art_id, a["title"]))
            path = base + ".jpg"
            print(f"[{art_id}] {a['title'][:50]}", flush=True)
            page = fetch(a["url"])
            if page is None:
                fail += 1
                continue
            img_url = extract_image_url(page.text)
            if not img_url:
                print("    [warn] 未找到配图", flush=True)
                fail += 1
                continue
            if download_image(img_url, path):
                # 修正实际扩展名（download_image 可能改写了 .jpg -> .webp/.png）
                for ext in ("webp", "png", "jpg"):
                    p = path.rsplit(".", 1)[0] + "." + ext
                    if os.path.exists(p):
                        a["image"] = f"images/{os.path.basename(p)}"
                        ok += 1
                        print("    ->", a["image"], flush=True)
                        break
            else:
                fail += 1
                print("    [warn] 下载失败", flush=True)
            time.sleep(DELAY)

    json.dump(data, open(JSON_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n完成: 成功 {ok} / 失败 {fail} / 跳过 {skipped}")


if __name__ == "__main__":
    main()
