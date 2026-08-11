/* ===== ChoiceGuide 前端逻辑 ===== */

// 图片使用站点生成的配图地址（prompt 由 encodeURIComponent 编码，保证 URL 合法）
function articleImage(prompt) {
  return (
    "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=" +
    encodeURIComponent(prompt) +
    "&image_size=landscape_16_9"
  );
}

// 文章数据：以后更新导购文章，只需在此处新增/修改对象即可
const articles = [
  {
    id: 1,
    title: "2026 年手机选购指南：旗舰机与性价比机怎么选？",
    excerpt: "从处理器、屏幕、影像到续航，用数据拆解每个价位的真实差距，拒绝参数陷阱。",
    category: "数码",
    featured: true,
    date: "2026-08-08",
    imagePrompt:
      "modern flagship smartphone lying on a minimalist desk with soft studio lighting, product photography, clean background",
  },
  {
    id: 2,
    title: "笔记本电脑避坑指南：轻薄本 / 全能本 / 游戏本",
    excerpt: "三大品类定位完全不同，先搞清楚需求再下单，否则多花几千块买了个负担。",
    category: "数码",
    featured: true,
    date: "2026-08-06",
    imagePrompt:
      "slim laptop half open on a bright wooden desk, minimalist workspace, warm natural light, product photography",
  },
  {
    id: 3,
    title: "家用咖啡机怎么选？意式半自动 vs 全自动实测对比",
    excerpt: "500 元到 5000 元跨度巨大，我们实测了主流机型，告诉你钱到底花在哪。",
    category: "家居",
    featured: true,
    date: "2026-08-03",
    imagePrompt:
      "espresso coffee machine brewing a cup on a kitchen counter, cozy morning light, food product photography",
  },
  {
    id: 4,
    title: "人体工学椅选购：腰托、头枕、网布，关键参数一篇讲透",
    excerpt: "久坐党的命是椅子给的。从调节范围到坐垫深度，手把手教你挑对型号。",
    category: "家居",
    featured: false,
    date: "2026-07-30",
    imagePrompt:
      "modern ergonomic office chair in a bright home office, clean minimal interior, soft daylight",
  },
  {
    id: 5,
    title: "护肤成分入门：烟酰胺、A 醇、玻尿酸，到底谁有效？",
    excerpt: "成分表不会骗人，但浓度和配方会。看懂这 10 个成分，护肤不再交智商税。",
    category: "美妆",
    featured: false,
    date: "2026-07-27",
    imagePrompt:
      "cosmetic serum bottles with droppers on a soft pastel background, beauty product photography, minimalist",
  },
  {
    id: 6,
    title: "空气炸锅 12 款横向测评：容量、功率、实测口感全记录",
    excerpt: "百元机和千元机的差距到底有多大？我们用 30 斤食材做完了这场测试。",
    category: "食品",
    featured: false,
    date: "2026-07-24",
    imagePrompt:
      "air fryer on a modern kitchen counter with fresh ingredients around, bright food photography",
  },
];

const categories = [
  { name: "数码", icon: "📱" },
  { name: "家居", icon: "🛋️" },
  { name: "美妆", icon: "💄" },
  { name: "食品", icon: "🍳" },
  { name: "生活", icon: "🏡" },
  { name: "全部", icon: "✨" },
];

/* ===== 渲染函数 ===== */
function renderFeatured() {
  const grid = document.getElementById("featuredGrid");
  const featured = articles.filter((a) => a.featured);
  grid.innerHTML = featured
    .map(
      (a) => `
    <article class="card" data-category="${a.category}">
      <img class="card-img" src="${articleImage(a.imagePrompt)}" alt="${a.title}" loading="lazy">
      <div class="card-body">
        <span class="card-tag">${a.category}</span>
        <h3 class="card-title">${a.title}</h3>
        <p class="card-excerpt">${a.excerpt}</p>
      </div>
    </article>`
    )
    .join("");
}

function renderCategories() {
  const grid = document.getElementById("categoryGrid");
  grid.innerHTML = categories
    .map((c) => {
      const count =
        c.name === "全部"
          ? articles.length
          : articles.filter((a) => a.category === c.name).length;
      return `
    <div class="category-item" data-category="${c.name}">
      <span class="category-icon">${c.icon}</span>
      <div class="category-name">${c.name}</div>
      <div class="category-count">${count} 篇文章</div>
    </div>`;
    })
    .join("");
}

function renderArticleList(list) {
  const container = document.getElementById("articleList");
  if (!list.length) {
    container.innerHTML = '<div class="empty-tip">没有找到相关文章，换个关键词试试。</div>';
    return;
  }
  container.innerHTML = list
    .map(
      (a) => `
    <div class="article-row" data-category="${a.category}">
      <img class="article-row-img" src="${articleImage(a.imagePrompt)}" alt="${a.title}" loading="lazy">
      <div class="article-row-info">
        <h3 class="article-row-title">${a.title}</h3>
        <p class="article-row-excerpt">${a.excerpt}</p>
        <div class="article-row-meta">${a.category} · ${a.date}</div>
      </div>
    </div>`
    )
    .join("");
}

/* ===== 搜索与筛选 ===== */
function filterArticles(keyword, category) {
  const kw = (keyword || "").trim().toLowerCase();
  return articles.filter((a) => {
    const matchKw = !kw || (a.title + a.excerpt + a.category).toLowerCase().includes(kw);
    const matchCat = !category || category === "全部" || a.category === category;
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

  function doSearch() {
    currentKeyword = input.value;
    applyFilter();
    document.getElementById("latest").scrollIntoView({ behavior: "smooth" });
  }

  btn.addEventListener("click", doSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
  });
}

function initCategories() {
  document.getElementById("categoryGrid").addEventListener("click", (e) => {
    const item = e.target.closest(".category-item");
    if (!item) return;
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
  renderArticleList(articles);
  initSearch();
  initCategories();
  initMobileNav();
});
