/* ===== 访问统计埋点（上报到内部看板服务器 /track） ===== */
(function () {
  // 生产环境改为看板服务的公网地址；本地开发用 localhost:8001
  var ENDPOINT = "http://localhost:8001/track";
  var page = location.pathname;
  var start = Date.now();
  var dwellSent = false;

  function send(data) {
    try {
      // text/plain 属于简单请求，避免 CORS 预检在页面跳转瞬间被丢弃
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

  // 3) 点击量（文章/页面链接点击）
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a");
    if (!a) return;
    var href = a.getAttribute("href") || "";
    if (href && /\.html/.test(href)) {
      send({ type: "click", page: page, target: href });
    }
  });
})();
