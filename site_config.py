# -*- coding: utf-8 -*-
"""
集中路径配置：网站目录 / 核心数据目录 / 看板目录。
默认值对应本机布局，可用环境变量覆盖：
  CHOICEGUIDE_SITE  = 网站根目录（部署到 Cloudflare Pages 的内容）
  CHOICEGUIDE_DATA  = 核心数据目录（爬取原始数据，不部署）
  CHOICEGUIDE_DASH  = 内部看板目录（不部署）
"""
import os

SITE_ROOT = os.environ.get("CHOICEGUIDE_SITE", r"c:\web01")
DATA_ROOT = os.environ.get("CHOICEGUIDE_DATA", r"c:\web01-data")
DASH_ROOT = os.environ.get("CHOICEGUIDE_DASH", r"c:\web01-dashboard")

SCRAPED_DIR = os.path.join(DATA_ROOT, "scraped")
ARTICLES_JSON = os.path.join(SCRAPED_DIR, "articles.json")
MARKDOWN_DIR = os.path.join(SCRAPED_DIR, "markdown")

IMAGES_DIR = os.path.join(SITE_ROOT, "images")
ARTICLES_DIR = os.path.join(SITE_ROOT, "articles")
JS_DIR = os.path.join(SITE_ROOT, "js")

HISTORY_PATH = os.path.join(DASH_ROOT, "data", "crawl-history.json")
DASHBOARD_OUT = os.path.join(DASH_ROOT, "js", "dashboard-data.js")
