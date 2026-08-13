/* ===== 访问统计埋点（上报到内部看板服务器 /track） ===== */
(function () {
  // Cloudflare Worker 端点：负责接收并写入 D1 数据库
  // 本地开发时可用 http://localhost:8001/track
  var ENDPOINT = "https://choiceguide-track.ttnf918.workers.dev/track";
  var TRACK_TOKEN = "cgtrack_6a7a9ed46eeefa9b3a36d612_20260812";
  var page = location.pathname;
  var start = Date.now();
  var dwellSent = false;

  function send(data) {
    try {
      // text/plain 属于简单请求，避免 CORS 预检在页面跳转瞬间被丢弃
      data.token = TRACK_TOKEN;
      var payload = JSON.stringify(data);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT, new Blob([payload], { type: "text/plain" }));
      } else {
        fetch(ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "text/plain" },
          body: payload,
          credentials: "omit",
          keepalive: true,
        });
      }
    } catch (e) {
      /* 埋点失败不影响页面 */
    }
  }

  // 1) 访问（页面浏览）
  send({ type: "pageview", page: page });

  // 2) 访问停留时长（离开页面时上报）
  function reportDwell() {
    if (dwellSent) return;
    dwellSent = true;
    send({ type: "dwell", page: page, dur: (Date.now() - start) / 1000 });
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") reportDwell();
  });
  window.addEventListener("pagehide", reportDwell);

  // 3) 真实广告点击统计
  // 广告为点击跳转型（iclick）：点击页面任意处可能跳转到外部广告域名，
  // 页面本身没有可见广告横幅。仅在实际触发广告跳转/弹窗时统计 ad_click：
  //   a) 点击站内文章链接 (.html)        -> click
  //   b) 点击外部域名链接 (target=_blank 等) -> ad_click
  //   c) 广告脚本 window.open 外部域名    -> ad_click（popunder 弹窗）
  //   d) 空白点击后页面发生跳转/卸载       -> ad_click（redirect 跳转型）
  var lastClickTs = 0;
  function onAnyClick(e) {
    var now = Date.now();
    if (now - lastClickTs < 300) return; // pointerdown 已统计，跳过紧随的 click
    lastClickTs = now;
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    var href = (a && a.getAttribute("href")) || "";
    var isArticle = /\.html/.test(href);
    var isExternal = /^https?:\/\//i.test(href) && href.indexOf(location.hostname) === -1;
    if (isArticle) {
      // 站内文章导航，正常点击
      send({ type: "click", page: page, target: href });
      lastNonArticleClick = 0;
    } else if (isExternal) {
      // 点击外部链接（广告落地页），直接统计
      send({ type: "ad_click", page: page, target: href });
      lastNonArticleClick = 0;
    } else {
      // 空白/非链接点击：若随后页面跳转（redirect 广告），在 pagehide 时补报
      lastNonArticleClick = now;
    }
  }
  var lastNonArticleClick = 0;
  document.addEventListener("click", onAnyClick, true);
  // 兼容点击被广告脚本 preventDefault 的场景：pointerdown 在 click 之前触发
  document.addEventListener("pointerdown", onAnyClick, true);

  // c) popunder 广告：广告脚本通过 window.open 打开外部广告页
  var _open = window.open;
  window.open = function (url) {
    try {
      if (typeof url === "string" && /^https?:\/\//i.test(url) && url.indexOf(location.hostname) === -1) {
        send({ type: "ad_click", page: page, target: url });
      }
    } catch (e) {}
    return _open.apply(this, arguments);
  };

  // d) redirect 广告：空白点击后页面发生跳转（pagehide），补报 ad_click
  window.addEventListener("pagehide", function () {
    if (lastNonArticleClick && Date.now() - lastNonArticleClick < 3000) {
      send({ type: "ad_click", page: page, target: "redirect-ad" });
    }
    lastNonArticleClick = 0;
  });
})();
