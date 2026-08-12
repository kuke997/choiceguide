/**
 * ChoiceGuide 访问统计 Worker（Cloudflare 边缘，本机不暴露）
 *
 * 接口：
 *   POST /track      网站埋点上报（公开，无 IP 限制；校验共享 Token + payload 大小 + 字段合法性）
 *   GET  /analytics  访问统计聚合（需 X-API-Key 头，密钥只存在本机 server.py）
 *
 * 定时任务：
 *   Cron 每 2 天执行一次，删除 2 天前的 track_events 记录，防止 D1 数据无限增长。
 *
 * 数据存储在 Cloudflare D1，不经过本地服务器。
 */
const MAX_BODY = 2048; // 正常浏览器上报远小于此，超过直接丢弃
const VALID_TYPES = new Set(["pageview", "dwell", "click", "ad_click"]);
// 保留最近 2 天的埋点数据（单位：秒）
const RETENTION_DAYS = 2;
const RETENTION_SECONDS = RETENTION_DAYS * 24 * 60 * 60;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (path === "/track" && request.method === "POST") {
      return handleTrack(request, env, ctx);
    }
    if (path === "/analytics" && request.method === "GET") {
      return handleAnalytics(request, env);
    }
    return new Response(JSON.stringify({ ok: false, error: "not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(cleanupOldEvents(env));
  },
};

function resp204() {
  return new Response(null, {
    status: 204,
    headers: { "Access-Control-Allow-Origin": "*" },
  });
}

async function handleTrack(request, env, ctx) {
  // 浏览器 sendBeacon 使用 text/plain（简单请求，无 CORS 预检）
  const ctype = request.headers.get("content-type") || "";
  if (!ctype.includes("text/plain")) return resp204();

  const raw = await request.text();
  if (!raw || raw.length > MAX_BODY) return resp204(); // 超大 payload 丢弃

  let ev;
  try {
    ev = JSON.parse(raw);
  } catch (e) {
    return resp204();
  }

  // 共享 Token 校验（track.js 内携带），不对 IP 做任何限制
  if (!ev.token || ev.token !== env.TRACK_TOKEN) return resp204();

  const type = ev.type;
  if (!VALID_TYPES.has(type)) return resp204();

  const page = typeof ev.page === "string" ? ev.page.slice(0, 300) : "";
  if (!page) return resp204();

  const target = typeof ev.target === "string" ? ev.target.slice(0, 300) : null;
  const dur =
    type === "dwell" && typeof ev.dur === "number" && ev.dur >= 0 && ev.dur <= 86400
      ? ev.dur
      : null;
  const ts = Math.floor(Date.now() / 1000);
  const ip = request.headers.get("CF-Connecting-IP") || "";

  // 解析 IP 地理位置（仅在 Cloudflare 边缘生效，本地开发时 request.cf 可能为空）
  const cf = request.cf || {};
  const country = (cf.country || "").toString().slice(0, 10);
  const city = (cf.city || "").toString().slice(0, 50);
  const region = (cf.region || cf.regionCode || "").toString().slice(0, 50);
  const isp = (cf.asOrganization || "").toString().slice(0, 100);
  const lon = cf.longitude ? parseFloat(cf.longitude) : null;
  const lat = cf.latitude ? parseFloat(cf.latitude) : null;

  ctx.waitUntil(
    env.DB.prepare(
      "INSERT INTO track_events (type, page, target, dur, ip, country, city, region, isp, lon, lat, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
      .bind(type, page, target, dur, ip, country, city, region, isp, lon, lat, ts)
      .run()
  );
  return resp204();
}

async function cleanupOldEvents(env) {
  const cutoff = Math.floor(Date.now() / 1000) - RETENTION_SECONDS;
  try {
    await env.DB.prepare("DELETE FROM track_events WHERE ts < ?")
      .bind(cutoff)
      .run();
  } catch (e) {
    console.error("cleanupOldEvents failed:", e);
  }
}

async function handleAnalytics(request, env) {
  if (request.headers.get("X-API-Key") !== env.ANALYTICS_KEY) {
    return new Response("Forbidden", { status: 403 });
  }

  const stats = {
    pageviews: 0,
    uniqueVisitors: 0,
    clicks: 0,
    adClicks: 0,
    dwellTotal: 0,
    dwellCount: 0,
    avgDwell: 0,
    dailyViews: {},
    pages: {},
    clicksByPage: {},
    adClicksByTarget: {},
    ips: {},
    ipDetails: [],
  };

  const [
    pvRow,
    uniqRow,
    clickRow,
    adClickRow,
    dwellRow,
    dailyRows,
    pageRows,
    clickRows,
    adClickRows,
    ipRows,
    ipDetailRows,
  ] = await Promise.all([
    env.DB.prepare("SELECT COUNT(*) AS c FROM track_events WHERE type='pageview'").first(),
    env.DB.prepare("SELECT COUNT(DISTINCT ip) AS c FROM track_events WHERE type='pageview'").first(),
    env.DB.prepare("SELECT COUNT(*) AS c FROM track_events WHERE type='click'").first(),
    env.DB.prepare("SELECT COUNT(*) AS c FROM track_events WHERE type='ad_click'").first(),
    env.DB.prepare("SELECT COALESCE(SUM(dur),0) AS s, COUNT(*) AS c FROM track_events WHERE type='dwell'").first(),
    env.DB.prepare("SELECT strftime('%Y-%m-%d', ts, 'unixepoch') AS day, COUNT(*) AS c FROM track_events WHERE type='pageview' GROUP BY day ORDER BY day").all(),
    env.DB.prepare("SELECT page, COUNT(*) AS c FROM track_events WHERE type='pageview' GROUP BY page ORDER BY c DESC LIMIT 10").all(),
    env.DB.prepare("SELECT target, COUNT(*) AS c FROM track_events WHERE type='click' GROUP BY target ORDER BY c DESC LIMIT 10").all(),
    env.DB.prepare("SELECT target, COUNT(*) AS c FROM track_events WHERE type='ad_click' GROUP BY target ORDER BY c DESC LIMIT 10").all(),
    env.DB.prepare("SELECT ip, COUNT(*) AS c FROM track_events WHERE type='pageview' GROUP BY ip ORDER BY c DESC LIMIT 15").all(),
    env.DB.prepare("SELECT ip, country, city, region, isp, COUNT(*) AS c, MIN(ts) AS first_ts, MAX(ts) AS last_ts FROM track_events WHERE type='pageview' GROUP BY ip ORDER BY c DESC").all(),
  ]);

  stats.pageviews = pvRow ? pvRow.c : 0;
  stats.uniqueVisitors = uniqRow ? uniqRow.c : 0;
  stats.clicks = clickRow ? clickRow.c : 0;
  stats.adClicks = adClickRow ? adClickRow.c : 0;
  stats.dwellTotal = dwellRow ? Math.round(dwellRow.s * 10) / 10 : 0;
  stats.dwellCount = dwellRow ? dwellRow.c : 0;
  stats.avgDwell = stats.dwellCount ? Math.round((stats.dwellTotal / stats.dwellCount) * 10) / 10 : 0;
  for (const r of dailyRows.results || []) stats.dailyViews[r.day] = r.c;
  for (const r of pageRows.results || []) stats.pages[r.page] = r.c;
  for (const r of clickRows.results || []) stats.clicksByPage[r.target] = r.c;
  for (const r of adClickRows.results || []) stats.adClicksByTarget[r.target] = r.c;
  for (const r of ipRows.results || []) stats.ips[r.ip] = r.c;
  stats.ipDetails = (ipDetailRows.results || []).map((r) => ({
    ip: r.ip,
    country: r.country || "-",
    city: r.city || "-",
    region: r.region || "-",
    isp: r.isp || "-",
    views: r.c,
    firstAt: r.first_ts ? new Date(r.first_ts * 1000).toISOString() : null,
    lastAt: r.last_ts ? new Date(r.last_ts * 1000).toISOString() : null,
  }));

  return new Response(JSON.stringify(stats), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
