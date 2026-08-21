/**
 * SGK E-Kesinti Otomasyon - License & IP Tracking API
 * Cloudflare Worker + D1 Database
 */

const ADMIN_PASSWORD_HASH = 'ESKI-HASH-KALDIRILDI'; // "***KALDIRILDI***" SHA-256
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    try {
      if (path === '/api/register' && request.method === 'POST') {
        return await handleRegister(request, env);
      }
      if (path === '/api/admin/users' && request.method === 'GET') {
        return await handleAdminUsers(url, env);
      }
      if (path === '/api/admin/authorize' && request.method === 'POST') {
        return await handleAdminAction(request, env, 'authorize');
      }
      if (path === '/api/admin/deauthorize' && request.method === 'POST') {
        return await handleAdminAction(request, env, 'deauthorize');
      }
      if (path === '/api/admin/stats' && request.method === 'GET') {
        return await handleStats(url, env);
      }
      if (path === '/admin' || path === '/admin/') {
        return await serveAdminPanel(env);
      }
      return jsonResponse({ error: 'Not found' }, 404);
    } catch (err) {
      return jsonResponse({ error: err.message || 'Internal error' }, 500);
    }
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

function sha256(str) {
  let buffer = new TextEncoder().encode(str);
  return crypto.subtle.digest('SHA-256', buffer).then(hash => {
    return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
  });
}

function verifyAdmin(url) {
  const password = url.searchParams.get('password') || '';
  return sha256(password).then(hash => hash === ADMIN_PASSWORD_HASH);
}

// --- POST /api/register ---
async function handleRegister(request, env) {
  const body = await request.json();
  const { hwid, ip } = body;

  if (!hwid || !ip) {
    return jsonResponse({ error: 'hwid and ip required', authorized: false }, 400);
  }

  if (!/^SGK-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$/i.test(hwid)) {
    return jsonResponse({ error: 'Invalid HWID format', authorized: false }, 400);
  }

  const now = new Date().toISOString();
  const existing = await env.DB.prepare('SELECT * FROM users WHERE hwid = ?').bind(hwid).first();

  if (existing) {
    await env.DB.prepare(
      'UPDATE users SET ip = ?, last_seen = ? WHERE hwid = ?'
    ).bind(ip, now, hwid).run();

    return jsonResponse({
      authorized: !!existing.authorized,
      message: existing.authorized ? 'Access granted' : 'HWID not authorized',
      hwid: existing.hwid,
      first_seen: existing.first_seen,
      last_seen: now,
    });
  }

  await env.DB.prepare(
    'INSERT INTO users (hwid, ip, first_seen, last_seen, authorized) VALUES (?, ?, ?, ?, 0)'
  ).bind(hwid, ip, now, now).run();

  return jsonResponse({
    authorized: false,
    message: 'HWID registered, pending authorization',
    hwid,
  }, 201);
}

// --- GET /api/admin/users ---
async function handleAdminUsers(url, env) {
  const isAuth = await verifyAdmin(url);
  if (!isAuth) return jsonResponse({ error: 'Unauthorized' }, 401);

  const rows = await env.DB.prepare('SELECT * FROM users ORDER BY last_seen DESC').all();
  return jsonResponse({ users: rows.results });
}

// --- POST /api/admin/authorize / deauthorize ---
async function handleAdminAction(request, env, action) {
  const body = await request.json();
  const { password, hwid } = body;

  if (!password || !hwid) {
    return jsonResponse({ error: 'password and hwid required' }, 400);
  }

  const hash = await sha256(password);
  if (hash !== ADMIN_PASSWORD_HASH) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  const val = action === 'authorize' ? 1 : 0;
  const result = await env.DB.prepare('UPDATE users SET authorized = ? WHERE hwid = ?')
    .bind(val, hwid).run();

  if (result.meta.changes === 0) {
    return jsonResponse({ error: 'HWID not found' }, 404);
  }

  return jsonResponse({
    success: true,
    message: action === 'authorize' ? 'HWID authorized' : 'HWID deauthorized',
    hwid,
  });
}

// --- GET /api/admin/stats ---
async function handleStats(url, env) {
  const isAuth = await verifyAdmin(url);
  if (!isAuth) return jsonResponse({ error: 'Unauthorized' }, 401);

  const total = await env.DB.prepare('SELECT COUNT(*) as count FROM users').first();
  const authorized = await env.DB.prepare('SELECT COUNT(*) as count FROM users WHERE authorized = 1').first();
  const recent = await env.DB.prepare(
    "SELECT COUNT(*) as count FROM users WHERE last_seen > datetime('now', '-24 hours')"
  ).first();

  return jsonResponse({
    total_users: total.count,
    authorized_users: authorized.count,
    pending_users: total.count - authorized.count,
    active_24h: recent.count,
  });
}

// --- Admin Panel HTML ---
async function serveAdminPanel(env) {
  const html = `<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SGK Admin Panel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f0f0f;color:#e0e0e0;min-height:100vh}
.header{background:#1a1a1a;border-bottom:1px solid #333;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:18px;color:#c9a86c;font-weight:600}
.header .badge{background:#2d2d2d;border:1px solid #444;padding:4px 12px;border-radius:12px;font-size:12px;color:#aaa}
.login-overlay{position:fixed;inset:0;background:#0f0f0f;display:flex;align-items:center;justify-content:center;z-index:100}
.login-box{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:32px;width:360px;text-align:center}
.login-box h2{color:#c9a86c;margin-bottom:20px;font-size:20px}
.login-box input{width:100%;padding:12px 16px;background:#111;border:1px solid #444;border-radius:8px;color:#fff;font-size:14px;margin-bottom:12px}
.login-box button{width:100%;padding:12px;background:#c9a86c;color:#111;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}
.login-box button:hover{background:#dbb978}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 24px}
.stat-card{background:#1a1a1a;border:1px solid #333;border-radius:8px;padding:16px;text-align:center}
.stat-card .num{font-size:28px;font-weight:700;color:#c9a86c}
.stat-card .label{font-size:12px;color:#888;margin-top:4px}
.toolbar{padding:12px 24px;display:flex;gap:8px;align-items:center}
.toolbar button{padding:8px 16px;border:1px solid #444;background:#1a1a1a;color:#ccc;border-radius:6px;cursor:pointer;font-size:13px}
.toolbar button:hover{border-color:#c9a86c;color:#c9a86c}
.toolbar input{padding:8px 12px;background:#111;border:1px solid #444;border-radius:6px;color:#fff;font-size:13px;width:200px}
table{width:100%;border-collapse:collapse}
th{background:#1a1a1a;padding:10px 16px;text-align:left;font-size:12px;color:#888;text-transform:uppercase;border-bottom:1px solid #333}
td{padding:10px 16px;border-bottom:1px solid #222;font-size:13px}
tr:hover{background:#1a1a1a}
.status{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.status.ok{background:#1b3a1b;color:#4caf50}
.status.pending{background:#3a2a0b;color:#ff9800}
.status.off{background:#3a1b1b;color:#f44336}
.action-btn{padding:4px 10px;border:1px solid #444;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:11px;margin-right:4px}
.action-btn:hover{border-color:#c9a86c;color:#c9a86c}
.hidden{display:none}
.table-wrap{padding:0 24px 24px}
.toast{position:fixed;bottom:20px;right:20px;background:#1a1a1a;border:1px solid #c9a86c;padding:12px 20px;border-radius:8px;font-size:13px;z-index:200;animation:fadeIn .3s}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>

<div class="login-overlay" id="loginOverlay">
<div class="login-box">
<h2>SGK Admin Panel</h2>
<input type="password" id="loginPass" placeholder="Admin sifresi" onkeydown="if(event.key==='Enter')doLogin()">
<button onclick="doLogin()">Giris Yap</button>
<p id="loginErr" style="color:#f44336;margin-top:8px;font-size:12px"></p>
</div>
</div>

<div class="hidden" id="mainPanel">
<div class="header">
<h1>SGK E-Kesinti | Admin Panel</h1>
<div class="badge" id="adminBadge"></div>
</div>
<div class="stats" id="statsRow">
<div class="stat-card"><div class="num" id="sTotal">-</div><div class="label">Toplam Kullanici</div></div>
<div class="stat-card"><div class="num" id="sAuth">-</div><div class="label">Yetkili</div></div>
<div class="stat-card"><div class="num" id="sPending">-</div><div class="label">Bekleyen</div></div>
<div class="stat-card"><div class="num" id="sActive">-</div><div class="label">Son 24s Aktif</div></div>
</div>
<div class="toolbar">
<button onclick="loadUsers()">Yenile</button>
<input type="text" id="searchBox" placeholder="HWID ara..." oninput="filterTable()">
<button onclick="showAddModal()">+ Yeni Kullanici</button>
</div>
<div class="table-wrap">
<table>
<thead><tr><th>HWID</th><th>IP</th><th>Ilk Gorulme</th><th>Son Gorulme</th><th>Durum</th><th>Islem</th></tr></thead>
<tbody id="userTable"></tbody>
</table>
</div>
</div>

<div class="login-overlay hidden" id="addModal">
<div class="login-box">
<h2>Yeni Kullanici Yetkilendir</h2>
<input type="text" id="addHwid" placeholder="SGK-XXXX-XXXX-XXXX-XXXX">
<button onclick="authorizeHwid()">Yetkilendir</button>
<p id="addErr" style="color:#f44336;margin-top:8px;font-size:12px"></p>
<button style="background:transparent;color:#888;border:1px solid #333;margin-top:8px" onclick="closeAddModal()">Iptal</button>
</div>
</div>

<script>
let ADMIN_PASS='';
function doLogin(){
  ADMIN_PASS=document.getElementById('loginPass').value;
  fetch('/api/admin/stats?password='+encodeURIComponent(ADMIN_PASS))
    .then(r=>r.json()).then(d=>{
      if(d.error){document.getElementById('loginErr').textContent='Hatali sifre';return}
      document.getElementById('loginOverlay').classList.add('hidden');
      document.getElementById('mainPanel').classList.remove('hidden');
      document.getElementById('adminBadge').textContent='Admin: ****';
      updateStats(d);loadUsers();
    }).catch(()=>{document.getElementById('loginErr').textContent='Baglanti hatasi'});
}
function updateStats(d){
  document.getElementById('sTotal').textContent=d.total_users;
  document.getElementById('sAuth').textContent=d.authorized_users;
  document.getElementById('sPending').textContent=d.pending_users;
  document.getElementById('sActive').textContent=d.active_24h;
}
function loadUsers(){
  fetch('/api/admin/users?password='+encodeURIComponent(ADMIN_PASS))
    .then(r=>r.json()).then(d=>{
      if(d.error)return;
      const tb=document.getElementById('userTable');
      tb.innerHTML='';
      d.users.forEach(u=>{
        const status=u.authorized?'<span class="status ok">AKTIF</span>':'<span class="status pending">BEKLIYOR</span>';
        const btn=u.authorized
          ?'<button class="action-btn" onclick="deauth(\\''+u.hwid+'\\')">Yetkiyi Kaldir</button>'
          :'<button class="action-btn" onclick="auth(\\''+u.hwid+'\\')">Yetkilendir</button>';
        tb.innerHTML+='<tr data-hwid="'+u.hwid.toUpperCase()+'"><td style="font-family:monospace;color:#c9a86c">'+u.hwid+'</td><td>'+u.ip+'</td><td>'+fmt(u.first_seen)+'</td><td>'+fmt(u.last_seen)+'</td><td>'+status+'</td><td>'+btn+'</td></tr>';
      });
    });
}
function fmt(s){if(!s)return'-';const d=new Date(s);return d.toLocaleDateString('tr-TR')+' '+d.toLocaleTimeString('tr-TR')}
function auth(hwid){
  fetch('/api/admin/authorize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:ADMIN_PASS,hwid})})
    .then(r=>r.json()).then(d=>{if(d.error)alert(d.error);else{toast(hwid+' yetkilendirildi');loadUsers();loadStats()}});
}
function deauth(hwid){
  if(!confirm(hwid+' yetkisi kaldirilsin mi?'))return;
  fetch('/api/admin/deauthorize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:ADMIN_PASS,hwid})})
    .then(r=>r.json()).then(d=>{if(d.error)alert(d.error);else{toast(hwid+' yetkisi kaldirildi');loadUsers();loadStats()}});
}
function loadStats(){
  fetch('/api/admin/stats?password='+encodeURIComponent(ADMIN_PASS))
    .then(r=>r.json()).then(d=>{if(!d.error)updateStats(d)});
}
function filterTable(){
  const q=document.getElementById('searchBox').value.toUpperCase();
  document.querySelectorAll('#userTable tr').forEach(r=>{
    r.style.display=r.dataset.hwid.includes(q)?'':'none';
  });
}
function showAddModal(){document.getElementById('addModal').classList.remove('hidden')}
function closeAddModal(){document.getElementById('addModal').classList.add('hidden');document.getElementById('addHwid').value=''}
function authorizeHwid(){
  const hwid=document.getElementById('addHwid').value.trim().toUpperCase();
  if(!hwid){document.getElementById('addErr').textContent='HWID girin';return}
  auth(hwid);closeAddModal();
}
function toast(msg){
  const t=document.createElement('div');t.className='toast';t.textContent=msg;document.body.appendChild(t);
  setTimeout(()=>t.remove(),3000);
}
</script>
</body>
</html>`;

  return new Response(html, {
    headers: { 'Content-Type': 'text/html; charset=utf-8', ...CORS_HEADERS },
  });
}
