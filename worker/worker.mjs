const H='37688acf5fd477512d3077e7043ba1cf2e6ef943affb2f8e0fc7c404afeb27e4';
const CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type'};

const HTML=`<!DOCTYPE html><html lang=tr><head><meta charset=UTF-8><meta name=viewport content="width=device-width,initial-scale=1"><title>SGK Yonetici Paneli</title><style>body{font-family:'Segoe UI',Arial,sans-serif;margin:20px;background:#f0f0f0}h1{color:#333}table{border-collapse:collapse;width:100%;background:#fff;margin-top:10px}th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:middle}th{background:#222;color:#fff}button{padding:6px 12px;margin:2px;cursor:pointer;border:none;border-radius:3px}.ok{background:#4caf50;color:#fff}.no{background:#f44336;color:#fff}.warn{background:#ff9800;color:#fff}#stats{margin:10px 0;font-weight:bold;color:#222}input{padding:6px}.namein{width:120px}</style></head><body><h1>SGK Yonetici Paneli</h1><div id=login><input id=pw type=password placeholder=Şifre><button onclick="login()">Giriş Yap</button><span id=msg></span></div><div id=panel style="display:none"><div id=stats></div><table id=tbl><tr><th>İsim/Not</th><th>HWID</th><th>IP</th><th>Durum</th><th>Son Görülme</th><th>İşlem</th></tr></table></div><script>window.onerror=function(m){var el=document.getElementById("msg");if(el)el.textContent="JS HATASI: "+m;};var PW="";function login(){PW=document.getElementById("pw").value;load();}function fmt(s){if(!s)return"-";var d=new Date(s);return d.toLocaleDateString("tr-TR")+" "+d.toLocaleTimeString("tr-TR");}function load(){fetch("/api/admin/stats?password="+encodeURIComponent(PW)).then(function(r){return r.json();}).then(function(s){if(s.error){document.getElementById("msg").textContent=s.error;return;}document.getElementById("stats").textContent="Toplam: "+s.total_users+" | Yetkili: "+s.authorized_users+" | Bekleyen: "+s.pending_users+" | 24s aktif: "+s.active_24h;}).catch(function(e){document.getElementById("msg").textContent="Hata: "+e;});fetch("/api/admin/users?password="+encodeURIComponent(PW)).then(function(r){return r.json();}).then(function(d){if(d.error){document.getElementById("msg").textContent=d.error;return;}document.getElementById("panel").style.display="block";var t=document.getElementById("tbl");for(var i=t.rows.length-1;i>0;i--){t.deleteRow(i);}d.users.forEach(function(u){var r=t.insertRow(-1);var c0=r.insertCell(0);c0.innerHTML='<input class=cuin value="'+(u.name||'')+'" id="n_'+u.hwid+'" onchange="saveName(\\''+u.hwid+'\\')">';r.insertCell(1).textContent=u.hwid;r.insertCell(2).textContent=u.ip;var s=r.insertCell(3);if(u.authorized)s.innerHTML='<span class=ok>Yetkili</span>';else s.innerHTML='<span class=warn>Bekliyor</span>';r.insertCell(4).textContent=fmt(u.last_seen);var c5=r.insertCell(5);if(u.authorized)c5.innerHTML='<button class=no onclick="deauth(\\''+u.hwid+'\\')">Yetkisi Kaldır</button>';else c5.innerHTML='<button class=ok onclick="auth(\\''+u.hwid+'\\')">Yetkilendir</button>';});}).catch(function(e){document.getElementById("msg").textContent="Hata: "+e;});}function saveName(h){var el=document.getElementById("n_"+h);var v=el.value;fetch("/api/admin/name",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:PW,hwid:h,name:v})}).then(function(r){return r.json();}).then(function(d){if(d.error)el.style.borderColor="#f44336";else el.style.borderColor="#4caf50";}).catch(function(){el.style.borderColor="#f44336";});}function auth(h){fetch("/api/admin/authorize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:PW,hwid:h})}).then(function(r){return r.json();}).then(function(d){if(d.error)alert(d.error);load();});}function deauth(h){if(!confirm("Yetkisi kaldirilsin mi?"))return;fetch("/api/admin/deauthorize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password:PW,hwid:h})}).then(function(r){return r.json();}).then(function(d){if(d.error)alert(d.error);load();});}</script></body></html>`;

export default{async fetch(r,e){
  var u=new URL(r.url);
  if(r.method==='OPTIONS')return new Response(null,{headers:CORS});
  try{
    if(u.pathname==='/api/register'&&r.method==='POST')return await reg(r,e);
    if(u.pathname==='/api/admin/users'&&r.method==='GET')return await users(u,e);
    if(u.pathname==='/api/admin/authorize'&&r.method==='POST')return await act(r,e,'authorize');
    if(u.pathname==='/api/admin/deauthorize'&&r.method==='POST')return await act(r,e,'deauthorize');
    if(u.pathname==='/api/admin/name'&&r.method==='POST')return await setname(r,e);
    if(u.pathname==='/api/admin/stats'&&r.method==='GET')return await stats(u,e);
    if(u.pathname==='/admin')return new Response(HTML,{headers:{'Content-Type':'text/html;charset=utf-8',...CORS}});
    return j({error:'Not found'},404);
  }catch(x){return j({error:x.message},500);}
}};

function j(d,s){return new Response(JSON.stringify(d),{status:s||200,headers:{'Content-Type':'application/json',...CORS}});}
function sha(s){return crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)).then(function(h){return Array.from(new Uint8Array(h)).map(function(b){return b.toString(16).padStart(2,'0')}).join('');});}
function adm(pw){return sha(pw).then(function(h){return h===H;});}

async function ensureName(e){
  try{await e.DB.prepare('ALTER TABLE users ADD COLUMN name TEXT DEFAULT ""').run();}catch(x){}
}

async function reg(r,e){
  var D=30,MS=D*24*3600*1000;
  var b=await r.json();
  if(!b.hwid||!b.ip)return j({error:'hwid and ip required',authorized:false},400);
  var n=new Date().toISOString();
  var x=await e.DB.prepare('SELECT * FROM users WHERE hwid=?').bind(b.hwid).first();
  if(x){
    await e.DB.prepare('UPDATE users SET ip=?,last_seen=? WHERE hwid=?').bind(b.ip,n,b.hwid).run();
    var demo=Date.now()-new Date(x.first_seen).getTime()<MS;
    var ok=!!x.authorized||demo;
    return j({authorized:ok,demo:demo&&!x.authorized,admin_authorized:!!x.authorized,demo_days_left:demo?Math.max(0,Math.ceil((MS-(Date.now()-new Date(x.first_seen).getTime()))/86400000)):0,msg:!!x.authorized?'Access granted':(demo?'Demo access (30 gun)':'Not authorized'),hwid:x.hwid,first:x.first_seen,last:n});
  }
  await e.DB.prepare('INSERT INTO users(hwid,ip,first_seen,last_seen,authorized)VALUES(?,?,?,?,0)').bind(b.hwid,b.ip,n,n).run();
  return j({authorized:true,demo:true,admin_authorized:false,demo_days_left:D,msg:'Demo access (30 gun)',hwid:b.hwid},201);
}

async function users(url,e){
  var pw=url.searchParams.get('password')||'';
  if(!(await adm(pw)))return j({error:'Unauthorized'},401);
  await ensureName(e);
  var r=await e.DB.prepare('SELECT * FROM users ORDER BY last_seen DESC').all();
  return j({users:r.results});
}

async function setname(r,e){
  var b=await r.json();
  if(!b.password||!b.hwid)return j({error:'password and hwid required'},400);
  if(!(await adm(b.password)))return j({error:'Unauthorized'},401);
  await ensureName(e);
  var x=await e.DB.prepare('UPDATE users SET name=? WHERE hwid=?').bind(b.name||'',b.hwid).run();
  if(x.meta.changes===0)return j({error:'HWID not found'},404);
  return j({ok:true,msg:'Name saved',hwid:b.hwid});
}

async function act(r,e,a){
  var b=await r.json();
  if(!b.password||!b.hwid)return j({error:'password and hwid required'},400);
  if(!(await adm(b.password)))return j({error:'Unauthorized'},401);
  var v=a==='authorize'?1:0;
  var x=await e.DB.prepare('UPDATE users SET authorized=? WHERE hwid=?').bind(v,b.hwid).run();
  if(x.meta.changes===0)return j({error:'HWID not found'},404);
  return j({ok:true,msg:a==='authorize'?'Authorized':'Deauthorized',hwid:b.hwid});
}

async function stats(url,e){
  var pw=url.searchParams.get('password')||'';
  if(!(await adm(pw)))return j({error:'Unauthorized'},401);
  var t=await e.DB.prepare('SELECT COUNT(*)as c FROM users').first();
  var a=await e.DB.prepare('SELECT COUNT(*)as c FROM users WHERE authorized=1').first();
  var r=await e.DB.prepare("SELECT COUNT(*)as c FROM users WHERE last_seen>datetime('now','-24 hours')").first();
  return j({total_users:t.c,authorized_users:a.c,pending_users:t.c-a.c,active_24h:r.c});
}