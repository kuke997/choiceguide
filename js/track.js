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

  // 3) 点击量（文章/页面链接点击 + 广告点击）
  // 广告为点击任意处跳转型（iclick 弹窗/跳转），页面无可见广告横幅，
  // 因此所有页面点击都记为广告点击 ad_click；站内文章链接点击另计为 click。
  // 使用捕获阶段监听，确保在广告脚本劫持点击/跳转之前先完成上报。
  // 同时监听 click 与 pointerdown（兼容被 preventDefault 的点击），用时间戳去重。
  var lastClickTs = 0;
  function onAnyClick(e) {
    var now = Date.now();
    if (now - lastClickTs < 300) return; // pointerdown 已统计，跳过紧随的 click
    lastClickTs = now;
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    var href = (a && a.getAttribute("href")) || "";
    var isArticle = /\.html/.test(href);
    if (isArticle) {
      send({ type: "click", page: page, target: href });
    }
    // 无论点击什么位置，都视为一次广告触发
    send({ type: "ad_click", page: page, target: href || "page-click" });
  }
  document.addEventListener("click", onAnyClick, true);
  // 兼容点击被广告脚本 preventDefault 的场景：pointerdown 在 click 之前触发
  document.addEventListener("pointerdown", onAnyClick, true);
})();
