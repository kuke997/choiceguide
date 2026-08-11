/* ===== ChoiceGuide 前端逻辑（对齐参考站 activebeat 版式） ===== */

// 文章数据：由爬取结果生成（见 js/articles-data.js，源数据在 scraped/articles.json）
const articles = (window.SCRAPED_DATA && window.SCRAPED_DATA.articles) || [];
const categories = (window.SCRAPED_DATA && window.SCRAPED_DATA.categories) || [];

// 按发布时间倒序排列（最新在前）
articles.sort((a, b) => (b.date || "").localeCompare(a.date || ""));

// 分类名 -> 图标
const categoryIcons = Object.fromEntries(categories.map((c) => [c.name, c.icon]));
function iconOf(category) {
  return categoryIcons[category] || "📄";
}
function authorsOf(a) {
  return a.authors && a.authors.length ? a.authors.join(", ") : "";
}
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}
// 配图优先，无图时回退到渐变封面
function thumbHtml(a, imgCls, fallbackCls, iconCls) {
  if (a.image) {
    return `<img class="${imgCls}" src="${a.image}" alt="${esc(a.title)}" loading="lazy">`;
  }
  return `<div class="${fallbackCls}" style="background:${a.cover}"><span class="${iconCls}">${iconOf(a.category)}</span></div>`;
}

/* ===== 1. 精选区：大卡 + 侧边两张小卡 ===== */
function renderFeatured() {
  const grid = document.getElementById("featuredGrid");
  const featured = articles.filter((a) => a.featured);
  const [big, ...rest] = featured;
  let html = "";
  if (big) {
    html += `
    <div class="feature-card">
      <a href="${big.page}">${thumbHtml(big, "feature-card__img", "feature-card__thumb", "feature-card__thumb-icon")}</a>
      <a class="post-category" href="#section-health-news">${big.category}</a>
      <h1 class="feature-card__title"><a href="${big.page}">${big.title}</a></h1>
      <p class="post-meta">By ${authorsOf(big) || "ChoiceGuide"} · ${big.read_time} · ${big.date}</p>
      <p class="feature-card__excerpt">${big.excerpt}</p>
    </div>`;
  }
  if (rest.length) {
    html += `<div class="feature-side">`;
    html += rest
      .map(
        (a) => `
      <div class="feature-card--small">
        <a href="${a.page}">${thumbHtml(a, "feature-card--small__img", "feature-card--small__thumb", "feature-card--small__thumb-icon")}</a>
        <a class="post-category" href="#section-health-news">${a.category}</a>
        <h3 class="feature-card--small__title"><a href="${a.page}">${a.title}</a></h3>
        <p class="post-meta">${a.read_time}</p>
      </div>`
      )
      .join("");
    html += `</div>`;
  }
  grid.innerHTML = html;
}

/* ===== 2. Health A-Z 瓦片 ===== */
function renderCategories() {
  const grid = document.getElementById("categoryGrid");
  grid.innerHTML = categories
    .map((c) => {
      const count =
        c.name === "All"
          ? articles.length
          : articles.filter((a) => a.category === c.name).length;
      return `
    <div class="category-item" data-category="${c.name}">
      <span class="category-icon">${c.icon}</span>
      <div>
        <div class="category-name">${c.name}</div>
        <div class="category-count">${count} articles</div>
      </div>
    </div>`;
    })
    .join("");
}

/* ===== 3. 分类内容区块 ===== */
function verticalCard(a) {
  return `
    <article class="post-card">
      <a href="${a.page}">${thumbHtml(a, "post-card__img", "post-card__thumb", "post-card__thumb-icon")}</a>
      <a class="post-category" href="#latest">${a.category}</a>
      <h3 class="post-card__title"><a href="${a.page}">${a.title}</a></h3>
      <p class="post-card__excerpt">${a.excerpt}</p>
      <p class="post-card__meta">By ${authorsOf(a) || "ChoiceGuide"} · ${a.read_time}</p>
    </article>`;
}

function horizontalRow(a) {
  return `
    <div class="post-row">
      <a href="${a.page}">${thumbHtml(a, "post-row__img", "post-row__thumb", "post-row__thumb-icon")}</a>
      <div>
        <a class="post-category" href="#latest">${a.category}</a>
        <h4 class="post-row__title"><a href="${a.page}">${a.title}</a></h4>
        <p class="post-row__meta">${a.read_time}</p>
      </div>
    </div>`;
}

function renderShowcase() {
  const container = document.getElementById("categorySections");
  const byCat = (name, n) => articles.filter((a) => a.category === name).slice(0, n);

  const sections = [
    { id: "section-health-news", subtitle: "Medically Reviewed", title: "Health News and Info", cats: ["Health News"], n: 6 },
    { id: "section-diet", subtitle: "Healthy Food", title: "Diet & Nutrition", cats: ["Diet & Nutrition"], n: 6 },
    { id: "section-fitness", subtitle: "Workout & Advice", title: "Fitness", cats: ["Fitness"], n: 6 },
  ];

  let html = "";
  for (const s of sections) {
    const items = [];
    for (const c of s.cats) items.push(...byCat(c, s.n));
    const cards = items.slice(0, s.n).map(verticalCard).join("");
    html += `
    <div class="section-block" id="${s.id}">
      <div class="section-head">
        <p class="section-subtitle">${s.subtitle}</p>
        <h2 class="section-title">${s.title}</h2>
      </div>
      <div class="showcase-grid">${cards}</div>
    </div>`;
  }

  // Your Health：分人群横向小卡
  const subCats = [
    ["Men", "Men"],
    ["Women", "Women"],
    ["Children", "Children"],
    ["Senior", "Senior"],
  ];
  let yh = `
    <div class="section-block" id="section-your-health">
      <div class="section-head">
        <p class="section-subtitle">For Everyone</p>
        <h2 class="section-title">Your Health</h2>
      </div>
      <div class="showcase-list">`;
  for (const [name] of subCats) {
    const rows = byCat(name, 2).map(horizontalRow).join("");
    yh += `<h3 class="showcase-sub">${name}</h3>${rows}`;
  }
  yh += `</div></div>`;

  container.innerHTML = html + yh;
}

/* ===== 4. 最新文章列表 ===== */
function renderArticleList(list) {
  const container = document.getElementById("articleList");
  if (!list.length) {
    container.innerHTML =
      '<div class="empty-tip">No articles found. Try a different keyword.</div>';
    return;
  }
  container.innerHTML = list
    .map(
      (a) => `
    <a class="article-row-link" href="${a.page}">
      <div class="article-row" data-category="${a.category}">
        ${thumbHtml(a, "article-row__img", "article-row-cover", "article-row-cover-icon")}
        <div class="article-row-info">
          <span class="article-row-category">${a.category}</span>
          <h3 class="article-row-title">${a.title}</h3>
          <p class="article-row-excerpt">${a.excerpt}</p>
          <div class="article-row-meta">By ${authorsOf(a) || "ChoiceGuide"} · ${a.read_time} · ${a.date}</div>
        </div>
      </div>
    </a>`
    )
    .join("");
}

/* ===== 搜索与筛选 ===== */
function filterArticles(keyword, category) {
  const kw = (keyword || "").trim().toLowerCase();
  return articles.filter((a) => {
    const matchKw = !kw || (a.title + a.excerpt + a.category).toLowerCase().includes(kw);
    const matchCat = !category || category === "All" || a.category === category;
    return matchKw && matchCat;
  });
}

let currentKeyword = "";
let currentCategory = "";

function applyFilter() {
  renderArticleList(filterArticles(currentKeyword, currentCategory));
}

/* ===== 事件绑定 ===== */
function initSearch() {
  const input = document.getElementById("searchInput");
  const btn = document.getElementById("searchBtn");
  const navBtn = document.getElementById("navSearchBtn");

  function doSearch() {
    currentKeyword = input.value;
    applyFilter();
    document.getElementById("latest").scrollIntoView({ behavior: "smooth" });
  }

  btn.addEventListener("click", doSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
  });
  navBtn.addEventListener("click", () => {
    currentKeyword = "";
    currentCategory = "";
    input.value = "";
    applyFilter();
    document.getElementById("latest").scrollIntoView({ behavior: "smooth" });
    input.focus();
  });
}

function initCategories() {
  document.getElementById("categoryGrid").addEventListener("click", (e) => {
    const item = e.target.closest(".category-item");
    if (!item) return;
    currentKeyword = "";
    document.getElementById("searchInput").value = "";
    currentCategory = item.dataset.category;
    applyFilter();
    document.getElementById("latest").scrollIntoView({ behavior: "smooth" });
  });
}

function initMobileNav() {
  const toggle = document.getElementById("navToggle");
  const nav = document.getElementById("mainNav");
  toggle.addEventListener("click", () => nav.classList.toggle("open"));
}

/* ===== 启动 ===== */
document.addEventListener("DOMContentLoaded", () => {
  renderFeatured();
  renderCategories();
  renderShowcase();
  renderArticleList(articles);
  initSearch();
  initCategories();
  initMobileNav();
});
