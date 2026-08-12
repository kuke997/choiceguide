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

  // 3) 点击量（文章/页面链接点击 + 外部广告点击）
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    var isArticle = /\.html/.test(href);
    var isExternal = /^https?:\/\//i.test(href) && href.indexOf(location.hostname) === -1;
    if (isArticle) {
      send({ type: "click", page: page, target: href });
    } else if (isExternal) {
      send({ type: "ad_click", page: page, target: href });
    }
  });
})();
