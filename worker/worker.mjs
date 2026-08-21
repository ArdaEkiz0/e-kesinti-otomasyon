const ADMIN_PASSWORD_HASH = 'ESKI-HASH-KALDIRILDI';
const CORS_HEADERS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' };

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS_HEADERS });
    try {
      if (path === '/api/register' && request.method === 'POST') return await handleRegister(request, env);
      if (path === '/api/admin/users' && request.method === 'GET') return await handleAdminUsers(url, env);
      if (path === '/api/admin/authorize' && request.method === 'POST') return await handleAdminAction(request, env, 'authorize');
      if (path === '/api/admin/deauthorize' && request.method === 'POST') return await handleAdminAction(request, env, 'deauthorize');
      if (path === '/api/admin/stats' && request.method === 'GET') return await handleStats(url, env);
      if (path === '/admin' || path === '/admin/') return await serveAdminPanel(env);
      return jsonResponse({ error: 'Not found' }, 404);
    } catch (err) { return jsonResponse({ error: err.message || 'Internal error' }, 500); }
  },
};

function jsonResponse(data, status) {
  return new Response(JSON.stringify(data), { status: status || 200, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS } });
}

function sha256(str) {
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function(hash) {
    return Array.from(new Uint8Array(hash)).map(function(b) { return b.toString(16).padStart(2, '0'); }).join('');
  });
}

function verifyAdmin(url) {
  var password = url.searchParams.get('password') || '';
  return sha256(password).then(function(hash) { return hash === ADMIN_PASSWORD_HASH; });
}

async function handleRegister(request, env) {
  var body = await request.json();
  var hwid = body.hwid;
  var ip = body.ip;
  if (!hwid || !ip) return jsonResponse({ error: 'hwid and ip required', authorized: false }, 400);
  if (!/^SGK-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$/i.test(hwid)) return jsonResponse({ error: 'Invalid HWID format', authorized: false }, 400);
  var now = new Date().toISOString();
  var existing = await env.DB.prepare('SELECT * FROM users WHERE hwid = ?').bind(hwid).first();
  if (existing) {
    await env.DB.prepare('UPDATE users SET ip = ?, last_seen = ? WHERE hwid = ?').bind(ip, now, hwid).run();
    return jsonResponse({ authorized: !!existing.authorized, message: existing.authorized ? 'Access granted' : 'HWID not authorized', hwid: existing.hwid, first_seen: existing.first_seen, last_seen: now });
  }
  await env.DB.prepare('INSERT INTO users (hwid, ip, first_seen, last_seen, authorized) VALUES (?, ?, ?, ?, 0)').bind(hwid, ip, now, now).run();
  return jsonResponse({ authorized: false, message: 'HWID registered, pending authorization', hwid: hwid }, 201);
}

async function handleAdminUsers(url, env) {
  var isAuth = await verifyAdmin(url);
  if (!isAuth) return jsonResponse({ error: 'Unauthorized' }, 401);
  var rows = await env.DB.prepare('SELECT * FROM users ORDER BY last_seen DESC').all();
  return jsonResponse({ users: rows.results });
}

async function handleAdminAction(request, env, action) {
  var body = await request.json();
  var password = body.password;
  var hwid = body.hwid;
  if (!password || !hwid) return jsonResponse({ error: 'password and hwid required' }, 400);
  var hash = await sha256(password);
  if (hash !== ADMIN_PASSWORD_HASH) return jsonResponse({ error: 'Unauthorized' }, 401);
  var val = action === 'authorize' ? 1 : 0;
  var result = await env.DB.prepare('UPDATE users SET authorized = ? WHERE hwid = ?').bind(val, hwid).run();
  if (result.meta.changes === 0) return jsonResponse({ error: 'HWID not found' }, 404);
  return jsonResponse({ success: true, message: action === 'authorize' ? 'HWID authorized' : 'HWID deauthorized', hwid: hwid });
}

async function handleStats(url, env) {
  var isAuth = await verifyAdmin(url);
  if (!isAuth) return jsonResponse({ error: 'Unauthorized' }, 401);
  var total = await env.DB.prepare('SELECT COUNT(*) as count FROM users').first();
  var authorized = await env.DB.prepare('SELECT COUNT(*) as count FROM users WHERE authorized = 1').first();
  var recent = await env.DB.prepare("SELECT COUNT(*) as count FROM users WHERE last_seen > datetime('now', '-24 hours')").first();
  return jsonResponse({ total_users: total.count, authorized_users: authorized.count, pending_users: total.count - authorized.count, active_24h: recent.count });
}

async function serveAdminPanel(env) {
  return new Response(getAdminHTML(), { headers: { 'Content-Type': 'text/html; charset=utf-8', ...CORS_HEADERS } });
}

function getAdminHTML() {
  var parts = [];
  parts.push('<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SGK Admin Panel</title>');
  parts.push('<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:"Segoe UI",system-ui,sans-serif;background:#0f0f0f;color:#e0e0e0;min-height:100vh}');
  parts.push('.header{background:#1a1a1a;border-bottom:1px solid #333;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}');
  parts.push('.header h1{font-size:18px;color:#c9a86c;font-weight:600}');
  parts.push('.header .badge{background:#2d2d2d;border:1px solid #444;padding:4px 12px;border-radius:12px;font-size:12px;color:#aaa}');
  parts.push('.login-overlay{position:fixed;inset:0;background:#0f0f0f;display:flex;align-items:center;justify-content:center;z-index:100}');
  parts.push('.login-box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:32px;width:360px;text-align:center}');
  parts.push('.login-box h2{color:#c9a86c;margin-bottom:20px;font-size:20px}');
  parts.push('.login-box input{width:100%;padding:12px 16px;background:#111;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;margin-bottom:12px}');
  parts.push('.login-box button{width:100%;padding:12px;background:#c9a86c;color:#111;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}');
  parts.push('.login-box button:hover{background:#dbb978}');
  parts.push('.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}');
  parts.push('.stat-card{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:16px;text-align:center}');
  parts.push('.stat-card .num{font-size:28px;font-weight:700;color:#c9a86c}');
  parts.push('.stat-card .label{font-size:12px;color:#888;margin-top:4px}');
  parts.push('.toolbar{padding:12px 24px;display:flex;gap:8px;align-items:center}');
  parts.push('.toolbar button{padding:8px 16px;border:1px solid #444;background:#1a1a1a;color:#ccc;border-radius:6px;cursor:pointer;font-size:13px}');
  parts.push('.toolbar button:hover{border-color:#c9a86c;color:#c9a86c}');
  parts.push('.toolbar input{padding:8px 12px;background:#111;border:1px solid #444;border-radius:6px;color:#fff;font-size:13px;width:200px}');
  parts.push('table{width:100%;border-collapse:collapse}');
  parts.push('th{background:#1a1a1a;padding:10px 16px;text-align:left;font-size:12px;color:#888;text-transform:uppercase;border-bottom:1px solid #333}');
  parts.push('td{padding:10px 16px;border-bottom:1px solid #222;font-size:13px}');
  parts.push('tr:hover{background:#1a1a1a}');
  parts.push('.status{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}');
  parts.push('.status.ok{background:#1b3a1b;color:#4caf50}');
  parts.push('.status.pending{background:#3a2a0b;color:#ff9800}');
  parts.push('.action-btn{padding:4px 10px;border:1px solid #444;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:11px;margin-right:4px}');
  parts.push('.action-btn:hover{border-color:#c9a86c;color:#c9a86c}');
  parts.push('.hidden{display:none}');
  parts.push('.table-wrap{padding:0 24px 24px}');
  parts.push('.toast{position:fixed;bottom:20px;right:20px;background:#1a1a1a;border:1px solid #c9a86c;padding:12px 20px;border-radius:8px;font-size:13px;z-index:200;animation:fadeIn .3s}');
  parts.push('@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}');
  parts.push('</style></head><body>');
  parts.push('<div class="login-overlay" id="loginOverlay"><div class="login-box"><h2>SGK Admin Panel</h2>');
  parts.push('<input type="password" id="loginPass" placeholder="Admin sifresi" onkeydown="if(event.key===\'Enter\')doLogin()">');
  parts.push('<button onclick="doLogin()">Giris Yap</button>');
  parts.push('<p id="loginErr" style="color:#f44336;margin-top:8px;font-size:12px"></p></div></div>');
  parts.push('<div class="hidden" id="mainPanel"><div class="header"><h1>SGK E-Kesinti | Admin Panel</h1>');
  parts.push('<div class="badge" id="adminBadge"></div></div>');
  parts.push('<div class="stats"><div class="stat-card"><div class="num" id="sTotal">-</div><div class="label">Toplam Kullanici</div></div>');
  parts.push('<div class="stat-card"><div class="num" id="sAuth">-</div><div class="label">Yetkili</div></div>');
  parts.push('<div class="stat-card"><div class="num" id="sPending">-</div><div class="label">Bekleyen</div></div>');
  parts.push('<div class="stat-card"><div class="num" id="sActive">-</div><div class="label">Son 24s Aktif</div></div></div>');
  parts.push('<div class="toolbar"><button onclick="loadUsers()">Yenile</button>');
  parts.push('<input type="text" id="searchBox" placeholder="HWID ara..." oninput="filterTable()">');
  parts.push('<button onclick="showAddModal()">+ Yeni Kullanici</button></div>');
  parts.push('<div class="table-wrap"><table><thead><tr><th>HWID</th><th>IP</th><th>Ilk Gorulme</th><th>Son Gorulme</th><th>Durum</th><th>Islem</th></tr></thead>');
  parts.push('<tbody id="userTable"></tbody></table></div></div>');
  parts.push('<div class="login-overlay hidden" id="addModal"><div class="login-box"><h2>Yeni Kullanici Yetkilendir</h2>');
  parts.push('<input type="text" id="addHwid" placeholder="SGK-XXXX-XXXX-XXXX-XXXX">');
  parts.push('<button onclick="authorizeHwid()">Yetkilendir</button>');
  parts.push('<p id="addErr" style="color:#f44336;margin-top:8px;font-size:12px"></p>');
  parts.push('<button style="background:transparent;color:#888;border:1px solid #333;margin-top:8px" onclick="closeAddModal()">Iptal</button>');
  parts.push('</div></div>');
  parts.push('<script>');
  parts.push('var ADMIN_PASS="";');
  parts.push('function doLogin(){ADMIN_PASS=document.getElementById("loginPass").value;');
  parts.push('fetch("/api/admin/stats?password="+encodeURIComponent(ADMIN_PASS))');
  parts.push('.then(function(r){return r.json()}).then(function(d){');
  parts.push('if(d.error){document.getElementById("loginErr").textContent="Hatali sifre";return}');
  parts.push('document.getElementById("loginOverlay").classList.add("hidden");');
  parts.push('document.getElementById("mainPanel").classList.remove("hidden");');
  parts.push('document.getElementById("adminBadge").textContent="Admin: ****";');
  parts.push('updateStats(d);loadUsers();');
  parts.push('}).catch(function(){document.getElementById("loginErr").textContent="Baglanti hatasi"});}');
  parts.push('function updateStats(d){document.getElementById("sTotal").textContent=d.total_users;');
  parts.push('document.getElementById("sAuth").textContent=d.authorized_users;');
  parts.push('document.getElementById("sPending").textContent=d.pending_users;');
  parts.push('document.getElementById("sActive").textContent=d.active_24h;}');
  parts.push('function loadUsers(){fetch("/api/admin/users?password="+encodeURIComponent(ADMIN_PASS))');
  parts.push('.then(function(r){return r.json()}).then(function(d){');
  parts.push('if(d.error)return;var tb=document.getElementById("userTable");tb.innerHTML="";');
  parts.push('d.users.forEach(function(u){');
  parts.push('var st=u.authorized?"<span class=\\"status ok\\">AKTIF</span>":"<span class=\\"status pending\\">BEKLIYOR</span>";');
  parts.push('var btn=u.authorized?"<button class=\\"action-btn\\" onclick=\\"deauth(\'"+u.hwid+"\')\\">Kaldir</button>":"<button class=\\"action-btn\\" onclick=\\"auth(\'"+u.hwid+"\')\\">Yetkilendir</button>";');
  parts.push('tb.innerHTML+="<tr data-hwid=\\""+u.hwid.toUpperCase()+"\\"><td style=\\"font-family:monospace;color:#c9a86c\\">"+u.hwid+"</td><td>"+u.ip+"</td><td>"+fmt(u.first_seen)+"</td><td>"+fmt(u.last_seen)+"</td><td>"+st+"</td><td>"+btn+"</td></tr>";'); 
  parts.push('});});}');
  parts.push('function fmt(s){if(!s)return"-";var d=new Date(s);return d.toLocaleDateString("tr-TR")+" "+d.toLocaleTimeString("tr-TR");}');
  parts.push('function auth(hwid){fetch("/api/admin/authorize",{method:"POST",headers:{"Content-Type":"application/json"},');
  parts.push('body:JSON.stringify({password:ADMIN_PASS,hwid:hwid})}).then(function(r){return r.json()}).then(function(d){');
  parts.push('if(d.error)alert(d.error);else{toast(hwid+" yetkilendirildi");loadUsers();loadStats();}});}');
  parts.push('function deauth(hwid){if(!confirm(hwid+" yetkisi kaldirilsin mi?"))return;');
  parts.push('fetch("/api/admin/deauthorize",{method:"POST",headers:{"Content-Type":"application/json"},');
  parts.push('body:JSON.stringify({password:ADMIN_PASS,hwid:hwid})}).then(function(r){return r.json()}).then(function(d){');
  parts.push('if(d.error)alert(d.error);else{toast(hwid+" yetkisi kaldirildi");loadUsers();loadStats();}});}');
  parts.push('function loadStats(){fetch("/api/admin/stats?password="+encodeURIComponent(ADMIN_PASS))');
  parts.push('.then(function(r){return r.json()}).then(function(d){if(!d.error)updateStats(d);});}');
  parts.push('function filterTable(){var q=document.getElementById("searchBox").value.toUpperCase();');
  parts.push('document.querySelectorAll("#userTable tr").forEach(function(r){');
  parts.push('r.style.display=r.dataset.hwid.indexOf(q)>=0?"":"none";});}');
  parts.push('function showAddModal(){document.getElementById("addModal").classList.remove("hidden");}');
  parts.push('function closeAddModal(){document.getElementById("addModal").classList.add("hidden");document.getElementById("addHwid").value="";}');
  parts.push('function authorizeHwid(){var hwid=document.getElementById("addHwid").value.trim().toUpperCase();');
  parts.push('if(!hwid){document.getElementById("addErr").textContent="HWID girin";return;}');
  parts.push('auth(hwid);closeAddModal();}');
  parts.push('function toast(msg){var t=document.createElement("div");t.className="toast";t.textContent=msg;');
  parts.push('document.body.appendChild(t);setTimeout(function(){t.remove();},3000);}');
  parts.push('</script></body></html>');
  return parts.join('');
}
