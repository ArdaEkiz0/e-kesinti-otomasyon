const H = "ESKI-HASH-KALDIRILDI";
const CR = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type"
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { headers: CR });
    try {
      if (url.pathname === "/api/register" && request.method === "POST") return await handleRegister(request, env);
      if (url.pathname === "/api/admin/users" && request.method === "GET") return await handleUsers(url, env);
      if (url.pathname === "/api/admin/authorize" && request.method === "POST") return await handleAction(request, env, "authorize");
      if (url.pathname === "/api/admin/deauthorize" && request.method === "POST") return await handleAction(request, env, "deauthorize");
      if (url.pathname === "/api/admin/stats" && request.method === "GET") return await handleStats(url, env);
      if (url.pathname === "/admin") return new Response(getHTML(), { headers: { "Content-Type": "text/html;charset=utf-8", ...CR } });
      return jsonResp({ error: "Not found" }, 404);
    } catch (err) { return jsonResp({ error: err.message }, 500); }
  }
};

function jsonResp(data, status) {
  return new Response(JSON.stringify(data), { status: status || 200, headers: { "Content-Type": "application/json", ...CR } });
}

function sha256(str) {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(str)).then(function(hash) {
    return Array.from(new Uint8Array(hash)).map(function(b) { return b.toString(16).padStart(2, "0"); }).join("");
  });
}

function checkAdmin(url) {
  var pw = url.searchParams.get("password") || "";
  return sha256(pw).then(function(h) { return h === H; });
}

async function handleRegister(request, env) {
  var body = await request.json();
  if (!body.hwid || !body.ip) return jsonResp({ error: "hwid and ip required", authorized: false }, 400);
  if (!/^SGK-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$/i.test(body.hwid)) return jsonResp({ error: "Invalid HWID", authorized: false }, 400);
  var now = new Date().toISOString();
  var existing = await env.DB.prepare("SELECT * FROM users WHERE hwid = ?").bind(body.hwid).first();
  if (existing) {
    await env.DB.prepare("UPDATE users SET ip = ?, last_seen = ? WHERE hwid = ?").bind(body.ip, now, body.hwid).run();
    return jsonResp({ authorized: !!existing.authorized, message: existing.authorized ? "Access granted" : "Not authorized", hwid: existing.hwid, first_seen: existing.first_seen, last_seen: now });
  }
  await env.DB.prepare("INSERT INTO users (hwid, ip, first_seen, last_seen, authorized) VALUES (?, ?, ?, ?, 0)").bind(body.hwid, body.ip, now, now).run();
  return jsonResp({ authorized: false, message: "Pending authorization", hwid: body.hwid }, 201);
}

async function handleUsers(url, env) {
  if (!(await checkAdmin(url))) return jsonResp({ error: "Unauthorized" }, 401);
  var rows = await env.DB.prepare("SELECT * FROM users ORDER BY last_seen DESC").all();
  return jsonResp({ users: rows.results });
}

async function handleAction(request, env, action) {
  var body = await request.json();
  if (!body.password || !body.hwid) return jsonResp({ error: "password and hwid required" }, 400);
  if ((await sha256(body.password)) !== H) return jsonResp({ error: "Unauthorized" }, 401);
  var val = action === "authorize" ? 1 : 0;
  var result = await env.DB.prepare("UPDATE users SET authorized = ? WHERE hwid = ?").bind(val, body.hwid).run();
  if (result.meta.changes === 0) return jsonResp({ error: "HWID not found" }, 404);
  return jsonResp({ success: true, message: action === "authorize" ? "Authorized" : "Deauthorized", hwid: body.hwid });
}

async function handleStats(url, env) {
  if (!(await checkAdmin(url))) return jsonResp({ error: "Unauthorized" }, 401);
  var total = await env.DB.prepare("SELECT COUNT(*) as c FROM users").first();
  var auth = await env.DB.prepare("SELECT COUNT(*) as c FROM users WHERE authorized = 1").first();
  var recent = await env.DB.prepare("SELECT COUNT(*) as c FROM users WHERE last_seen > datetime('now', '-24 hours')").first();
  return jsonResp({ total_users: total.c, authorized_users: auth.c, pending_users: total.c - auth.c, active_24h: recent.c });
}

function getHTML() {
  return '<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SGK Admin Panel</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:"Segoe UI",system-ui,sans-serif;background:#0f0f0f;color:#e0e0e0;min-height:100vh}.header{background:#1a1a1a;border-bottom:1px solid #333;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}.header h1{font-size:18px;color:#c9a86c;font-weight:600}.header .badge{background:#2d2d2d;border:1px solid #444;padding:4px 12px;border-radius:12px;font-size:12px;color:#aaa}.login-overlay{position:fixed;inset:0;background:#0f0f0f;display:flex;align-items:center;justify-content:center;z-index:100}.login-box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:32px;width:360px;text-align:center}.login-box h2{color:#c9a86c;margin-bottom:20px;font-size:20px}.login-box input{width:100%;padding:12px 16px;background:#111;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;margin-bottom:12px}.login-box button{width:100%;padding:12px;background:#c9a86c;color:#111;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}.login-box button:hover{background:#dbb978}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}.stat-card{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:16px;text-align:center}.stat-card .num{font-size:28px;font-weight:700;color:#c9a86c}.stat-card .label{font-size:12px;color:#888;margin-top:4px}.toolbar{padding:12px 24px;display:flex;gap:8px;align-items:center}.toolbar button{padding:8px 16px;border:1px solid #444;background:#1a1a1a;color:#ccc;border-radius:6px;cursor:pointer;font-size:13px}.toolbar button:hover{border-color:#c9a86c;color:#c9a86c}.toolbar input{padding:8px 12px;background:#111;border:1px solid #444;border-radius:6px;color:#fff;font-size:13px;width:200px}table{width:100%;border-collapse:collapse}th{background:#1a1a1a;padding:10px 16px;text-align:left;font-size:12px;color:#888;text-transform:uppercase;border-bottom:1px solid #333}td{padding:10px 16px;border-bottom:1px solid #222;font-size:13px}tr:hover{background:#1a1a1a}.status{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}.status.ok{background:#1b3a1b;color:#4caf50}.status.pending{background:#3a2a0b;color:#ff9800}.action-btn{padding:4px 10px;border:1px solid #444;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:11px;margin-right:4px}.action-btn:hover{border-color:#c9a86c;color:#c9a86c}.hidden{display:none}.table-wrap{padding:0 24px 24px}.toast{position:fixed;bottom:20px;right:20px;background:#1a1a1a;border:1px solid #c9a86c;padding:12px 20px;border-radius:8px;font-size:13px;z-index:200;animation:fadeIn .3s}@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}</style></head><body><div class="login-overlay" id="loginOverlay"><div class="login-box"><h2>SGK Admin Panel</h2><input type="password" id="loginPass" placeholder="Admin sifresi"><button onclick="doLogin()">Giris Yap</button><p id="loginErr" style="color:#f44336;margin-top:8px;font-size:12px"></p></div></div><div class="hidden" id="mainPanel"><div class="header"><h1>SGK E-Kesinti | Admin Panel</h1><div class="badge" id="adminBadge"></div></div><div class="stats"><div class="stat-card"><div class="num" id="sTotal">-</div><div class="label">Toplam Kullanici</div></div><div class="stat-card"><div class="num" id="sAuth">-</div><div class="label">Yetkili</div></div><div class="stat-card"><div class="num" id="sPending">-</div><div class="label">Bekleyen</div></div><div class="stat-card"><div class="num" id="sActive">-</div><div class="label">Son 24s Aktif</div></div></div><div class="toolbar"><button onclick="loadUsers()">Yenile</button><input type="text" id="searchBox" placeholder="HWID ara..." oninput="filterTable()"><button onclick="showAddModal()">+ Yeni Kullanici</button></div><div class="table-wrap"><table><thead><tr><th>HWID</th><th>IP</th><th>Ilk Gorulme</th><th>Son Gorulme</th><th>Durum</th><th>Islem</th></tr></thead><tbody id="userTable"></tbody></table></div></div><div class="login-overlay hidden" id="addModal"><div class="login-box"><h2>Yeni Kullanici Yetkilendir</h2><input type="text" id="addHwid" placeholder="SGK-XXXX-XXXX-XXXX-XXXX"><button onclick="authorizeHwid()">Yetkilendir</button><p id="addErr" style="color:#f44336;margin-top:8px;font-size:12px"></p><button style="background:transparent;color:#888;border:1px solid #333;margin-top:8px" onclick="closeAddModal()">Iptal</button></div></div><script>var ADMIN_PASS="";function doLogin(){ADMIN_PASS=document.getElementById("loginPass").value;fetch("/api/admin/stats?password="+encodeURIComponent(ADMIN_PASS)).then(function(r){return r.json()}).then(function(d){if(d.error){document.getElementById("loginErr").textContent="Hatali sifre";return}document.getElementById("loginOverlay").classList.add("hidden");document.getElementById("mainPanel").classList.remove("hidden");document.getElementById("adminBadge").textContent="Admin: ****";updateStats(d);loadUsers()}).catch(function(){document.getElementById("loginErr").textContent="Baglanti hatasi"})}function updateStats(d){document.getElementById("sTotal").textContent=d.total_users;document.getElementById("sAuth").textContent=d.authorized_users;document.getElementById("sPending").textContent=d.pending_users;document.getElementById("sActive").textContent=d.active_24h}function loadUsers(){fetch("/api/admin/users?password="+encodeURIComponent(ADMIN_PASS)).then(function(r){return r.json()}).then(function(d){if(d.error)return;var tb=document.getElementById("userTable");tb.innerHTML="";d.users.forEach(function(u){var st=u.authorized?"AKTIF":"BEKLEYEN";var cls=u.authorized?"status ok":"status pending";var btn=u.authorized?"<button class=\\"action-btn\\" onclick=\\"deauth('"+u.hwid+"')\\">Kaldir</button>":"<button class=\\"action-btn\\" onclick=\\"auth('"+u.hwid+"')\\">Yetkilendir</button>";tb.innerHTML+="<tr><td style=\\"font-family:monospace;color:#c9a86c\\">"+u.hwid+"</td><td>"+u.ip+"</td><td>"+u.first_seen+"</td><td>"+u.last_seen+"</td><td><span class=\\""+cls+"\\">"+st+"</span></td><td>"+btn+"</td></tr>"})})}function auth(hwid){fetch("/api/admin/authorize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:ADMIN_PASS,hwid:hwid})}).then(function(r){return r.json()}).then(function(d){if(d.error)alert(d.error);else{loadUsers()}})}function deauth(hwid){fetch("/api/admin/deauthorize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:ADMIN_PASS,hwid:hwid})}).then(function(r){return r.json()}).then(function(d){if(d.error)alert(d.error);else{loadUsers()}})}function filterTable(){var q=document.getElementById("searchBox").value.toUpperCase();document.querySelectorAll("#userTable tr").forEach(function(r){r.style.display=r.textContent.toUpperCase().indexOf(q)>=0?"":"none"})}function showAddModal(){document.getElementById("addModal").classList.remove("hidden")}function closeAddModal(){document.getElementById("addModal").classList.add("hidden");document.getElementById("addHwid").value=""}function authorizeHwid(){var hwid=document.getElementById("addHwid").value.trim().toUpperCase();if(hwid){auth(hwid);closeAddModal()}}</script></body></html>';
}
