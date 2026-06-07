"""Interface web completa do Portal Motorista (camada visual sobre APIs existentes)."""
from __future__ import annotations

import json

from .driver_portal_dtos import portal_branding
from .portal_auth import driver_has_password


def render_driver_portal_page(app, driver, slug):
    branding = portal_branding(app)
    empresa = branding["empresa"]
    logo_url = branding.get("logo_url") or ""
    logo_inner = f'<img src="{logo_url}" alt="logo"/>' if logo_url else empresa[:1]
    activated = driver_has_password(driver)
    html = _HTML.replace("__SLUG__", json.dumps(slug))
    html = html.replace("__ACTIVATED__", "true" if activated else "false")
    html = html.replace("__LOGO_URL__", json.dumps(logo_url))
    html = html.replace("__EMPRESA__", empresa)
    html = html.replace("__BUILD__", branding["build"])
    html = html.replace("__DRIVER_NOME__", driver.get("nome", "Motorista"))
    html = html.replace("__CPF_HINT__", driver.get("cpf", ""))
    html = html.replace("__LOGO_INNER__", logo_inner)
    html = html.replace("__ACTIVATION_MSG__", "" if activated else "Portal ainda nao ativado. Solicite o token de ativacao ao administrador.")
    return html


_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Portal Motorista — __EMPRESA__</title>
<style>
:root{--bg:#0f1419;--panel:#1a2332;--panel2:#243044;--text:#e8eef7;--muted:#8fa3bf;--primary:#3b82f6;--primary-dark:#2563eb;--success:#22c55e;--warning:#f59e0b;--danger:#ef4444;--line:#2d3a4f;--radius:14px;--shadow:0 8px 32px rgba(0,0,0,.35)}
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.hidden{display:none!important}.app{max-width:1100px;margin:0 auto;min-height:100vh;display:flex;flex-direction:column}
.topbar{background:var(--panel);border-bottom:1px solid var(--line);padding:14px 18px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:10}
.logo{width:42px;height:42px;border-radius:10px;background:var(--panel2);display:grid;place-items:center;font-weight:700;color:var(--primary);overflow:hidden}
.logo img{width:100%;height:100%;object-fit:cover}.brand h1{margin:0;font-size:1rem}.brand p{margin:2px 0 0;font-size:.78rem;color:var(--muted)}
.spacer{flex:1}.chip{font-size:.72rem;padding:4px 10px;border-radius:999px;background:var(--panel2);color:var(--muted)}
.content{flex:1;padding:16px;padding-bottom:88px}.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);margin-bottom:14px}
.grid{display:grid;gap:12px}.grid-4{grid-template-columns:repeat(4,1fr)}@media(max-width:768px){.grid-4{grid-template-columns:repeat(2,1fr)}}
.stat{text-align:center}.stat .val{font-size:1.6rem;font-weight:700;color:var(--primary)}.stat .lbl{font-size:.78rem;color:var(--muted);margin-top:4px}
label{display:block;font-size:.82rem;color:var(--muted);margin-bottom:6px}input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid var(--line);background:var(--panel2);color:var(--text);font-size:.95rem}
button{cursor:pointer;border:none;border-radius:10px;padding:12px 16px;font-weight:600;font-size:.92rem}
.btn{background:var(--primary);color:#fff}.btn-outline{background:transparent;border:1px solid var(--line);color:var(--text)}.btn-success{background:var(--success);color:#fff}.btn-block{width:100%}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.nav{position:fixed;bottom:0;left:0;right:0;background:var(--panel);border-top:1px solid var(--line);display:flex;justify-content:space-around;padding:8px 6px 10px;z-index:20}
.nav button{background:transparent;color:var(--muted);font-size:.72rem;display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px 10px}.nav button.active{color:var(--primary)}
.table{width:100%;border-collapse:collapse;font-size:.88rem}.table th,.table td{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.badge{display:inline-block;padding:3px 8px;border-radius:999px;font-size:.72rem;background:var(--panel2)}.badge.ok{background:rgba(34,197,94,.15);color:var(--success)}.badge.warn{background:rgba(245,158,11,.15);color:var(--warning)}.badge.err{background:rgba(239,68,68,.15);color:var(--danger)}
.notice{border-left:3px solid var(--primary);padding:10px 12px;background:var(--panel2);border-radius:8px;margin-bottom:10px}.notice.unread{border-left-color:var(--warning)}
.login-wrap{max-width:420px;margin:40px auto}.muted{color:var(--muted);font-size:.85rem}.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.filters button{padding:8px 12px}.filters button.active{background:var(--primary);color:#fff}
.detail-row{display:grid;grid-template-columns:120px 1fr;gap:8px;margin-bottom:8px;font-size:.9rem}.alert{padding:10px 12px;border-radius:8px;margin-bottom:12px;font-size:.85rem}.alert.err{background:rgba(239,68,68,.12);color:#fecaca}
</style>
</head>
<body>
<div class="app">
<header class="topbar">
<div class="logo" id="logoBox">__LOGO_INNER__</div>
<div class="brand"><h1>__EMPRESA__</h1><p>Portal Motorista · Build __BUILD__</p></div>
<div class="spacer"></div><span class="chip" id="driverChip">__DRIVER_NOME__</span>
<button class="btn-outline hidden" id="logoutBtn" type="button">Sair</button>
</header>
<main class="content">
<section id="view-login" class="login-wrap"><div class="card">
<h2>Entrar no portal</h2><p class="muted">Motorista: <strong>__DRIVER_NOME__</strong></p>
<div id="loginAlert" class="alert err hidden"></div>
<label for="cpf">CPF ou identificação</label><input id="cpf" inputmode="numeric" placeholder="000.000.000-00" value="__CPF_HINT__"/>
<label for="password" style="margin-top:12px">Senha</label><input id="password" type="password" placeholder="Sua senha do portal"/>
<button class="btn btn-block" id="loginBtn" type="button" style="margin-top:16px">Entrar</button>
<p class="muted" style="margin-top:14px">__ACTIVATION_MSG__</p>
</div></section>
<section id="view-dashboard" class="hidden">
<div class="grid grid-4">
<div class="card stat"><div class="val" id="cardHoje">0</div><div class="lbl">Reservas Hoje</div></div>
<div class="card stat"><div class="val" id="cardProximas">0</div><div class="lbl">Próximas</div></div>
<div class="card stat"><div class="val" id="cardConcluidas">0</div><div class="lbl">Concluídas</div></div>
<div class="card stat"><div class="val" id="cardPendentes">0</div><div class="lbl">Pendentes</div></div>
</div>
<div class="card"><h3 style="margin:0 0 12px">Indicadores</h3>
<div class="detail-row"><span class="muted">Status portal</span><span id="indPortal">—</span></div>
<div class="detail-row"><span class="muted">Último acesso</span><span id="indAcesso">—</span></div>
<div class="detail-row"><span class="muted">Cidade principal</span><span id="indCidade">—</span></div></div>
<div class="card"><h3 style="margin:0 0 12px">Próximas reservas</h3><div id="dashList"></div></div>
</section>
<section id="view-agenda" class="hidden">
<div class="filters"><button type="button" class="active" data-filter="all">Todas</button><button type="button" data-filter="today">Hoje</button><button type="button" data-filter="week">Semana</button><button type="button" data-filter="month">Mês</button></div>
<div class="card" style="overflow-x:auto"><table class="table"><thead><tr><th>Data</th><th>Hora</th><th>Cliente</th><th>Empresa</th><th>Origem</th><th>Destino</th><th>Status</th></tr></thead><tbody id="agendaBody"></tbody></table></div>
</section>
<section id="view-detail" class="hidden"><div class="card" id="detailCard"></div></section>
<section id="view-profile" class="hidden"><div class="card" id="profileCard"></div></section>
<section id="view-documents" class="hidden"><div class="card"><h3>Documentos</h3><p class="muted">Upload em versão futura.</p><div id="docsList"></div></div></section>
<section id="view-notifications" class="hidden"><div class="card"><h3>Notificações</h3><div id="notifList"></div></div></section>
</main>
<nav class="nav hidden" id="bottomNav">
<button type="button" data-view="dashboard"><span>⌂</span>Dashboard</button>
<button type="button" data-view="agenda"><span>📅</span>Agenda</button>
<button type="button" data-view="notifications"><span>🔔</span>Avisos</button>
<button type="button" data-view="profile"><span>👤</span>Perfil</button>
</nav>
</div>
<script>
const SLUG=__SLUG__;const ACTIVATED=__ACTIVATED__;const LOGO_URL=__LOGO_URL__;
let token=sessionStorage.getItem('driver_token')||'';let reservations=[];let agendaFilter='all';
function $(id){return document.getElementById(id)}function show(el){el.classList.remove('hidden')}function hide(el){el.classList.add('hidden')}
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:SLUG,token,...body})});return r.json()}
function setView(name){['login','dashboard','agenda','detail','profile','documents','notifications'].forEach(v=>{const el=$('view-'+v);if(el)hide(el)});show($('view-'+name));document.querySelectorAll('#bottomNav button').forEach(b=>b.classList.toggle('active',b.dataset.view===name))}
function statusBadge(s){const v=(s||'').toLowerCase();let c='badge';if(v.includes('conclu'))c+=' ok';else if(v.includes('cancel'))c+=' err';else if(v.includes('pend')||v.includes('aceitar'))c+=' warn';return `<span class="${c}">${s||'—'}</span>`}
async function doLogin(){hide($('loginAlert'));const payload={slug:SLUG,cpf:$('cpf').value,identificacao:$('cpf').value,password:$('password').value};const res=await fetch('/api/driver/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(r=>r.json());if(!res.ok){show($('loginAlert'));$('loginAlert').textContent='CPF ou senha invalidos.';return}token=res.token;sessionStorage.setItem('driver_token',token);await bootApp()}
async function bootApp(){if(!token){setView('login');return}const dash=await api('/api/driver/dashboard');if(!dash.ok){token='';sessionStorage.removeItem('driver_token');setView('login');return}show($('bottomNav'));show($('logoutBtn'));renderDashboard(dash);await loadReservations();await loadNotifications();await loadProfile();setView('dashboard')}
function renderDashboard(d){$('cardHoje').textContent=d.cards.hoje;$('cardProximas').textContent=d.cards.proximas;$('cardConcluidas').textContent=d.cards.concluidas;$('cardPendentes').textContent=d.cards.pendentes;$('indPortal').textContent=d.indicators.portal_status;$('indAcesso').textContent=d.indicators.ultimo_acesso||'—';$('indCidade').textContent=[d.indicators.cidade_principal,d.indicators.estado].filter(Boolean).join(' / ')||'—';$('dashList').innerHTML=(d.proximas_reservas||[]).map(r=>`<div class="notice" style="cursor:pointer" data-num="${r.numero}"><strong>${r.numero}</strong> · ${r.data} · ${r.origem} → ${r.destino} ${statusBadge(r.status)}</div>`).join('')||'<p class="muted">Nenhuma reserva proxima.</p>';$('dashList').querySelectorAll('[data-num]').forEach(el=>el.onclick=()=>openDetail(el.dataset.num))}
async function loadReservations(){const res=await api('/api/driver/reservations');if(res.ok)reservations=res.items||[];renderAgenda()}
function parseBrDate(s){if(!s)return null;const p=String(s).trim().slice(0,10).split('/');if(p.length===3)return new Date(+p[2],+p[1]-1,+p[0]);return new Date(s)}
function filterReservations(list){const now=new Date();now.setHours(0,0,0,0);const week=new Date(now);week.setDate(week.getDate()+7);const month=new Date(now);month.setDate(month.getDate()+30);return list.filter(r=>{const d=parseBrDate(r.data);if(!d||isNaN(d))return agendaFilter==='all';d.setHours(0,0,0,0);if(agendaFilter==='today')return d.getTime()===now.getTime();if(agendaFilter==='week')return d>=now&&d<=week;if(agendaFilter==='month')return d>=now&&d<=month;return true})}
function renderAgenda(){const rows=filterReservations(reservations);$('agendaBody').innerHTML=rows.map(r=>`<tr style="cursor:pointer" data-num="${r.numero}"><td>${r.data||'—'}</td><td>${r.hora||'—'}</td><td>${r.cliente||'—'}</td><td>${r.empresa||'—'}</td><td>${r.origem||'—'}</td><td>${r.destino||'—'}</td><td>${statusBadge(r.status)}</td></tr>`).join('')||'<tr><td colspan="7" class="muted">Sem reservas.</td></tr>';$('agendaBody').querySelectorAll('[data-num]').forEach(el=>el.onclick=()=>openDetail(el.dataset.num))}
async function openDetail(numero){const res=await api('/api/driver/reservation',{numero});if(!res.ok)return alert('Reserva nao permitida.');const r=res.item;$('detailCard').innerHTML=`<h3>Reserva ${r.numero}</h3><div class="detail-row"><span class="muted">Cliente</span><span>${r.cliente||'—'}</span></div><div class="detail-row"><span class="muted">Empresa</span><span>${r.empresa||'—'}</span></div><div class="detail-row"><span class="muted">Data/Hora</span><span>${r.data||'—'} ${r.hora||''}</span></div><div class="detail-row"><span class="muted">Origem</span><span>${r.origem||'—'}</span></div><div class="detail-row"><span class="muted">Destino</span><span>${r.destino||'—'}</span></div><div class="detail-row"><span class="muted">Observações</span><span>${r.observacoes||'—'}</span></div><div class="actions"><a class="btn btn-outline" href="${r.maps_url}" target="_blank">Abrir rota</a></div><div class="actions" id="statusActions"></div>`;(res.actions||[]).forEach(a=>{const b=document.createElement('button');b.className='btn btn-success';b.textContent=a.label;b.onclick=()=>updateStatus(r.numero,a.status);$('statusActions').appendChild(b)});setView('detail')}
async function updateStatus(numero,status){const res=await api('/api/driver/status',{numero,status});if(!res.ok)return alert('Sem permissao.');await loadReservations();openDetail(numero)}
async function loadProfile(){const res=await api('/api/driver/profile');if(!res.ok)return;const p=res.profile;$('profileCard').innerHTML=`<h3>${p.nome}</h3><div class="detail-row"><span class="muted">CPF</span><span>${p.cpf_masked||p.cpf||'—'}</span></div><div class="detail-row"><span class="muted">Telefone</span><span>${p.telefone||'—'}</span></div><div class="detail-row"><span class="muted">E-mail</span><span>${p.email||'—'}</span></div><div class="detail-row"><span class="muted">Cidade/UF</span><span>${p.cidade||'—'} / ${p.estado||'—'}</span></div><div class="detail-row"><span class="muted">Validade CNH</span><span>${p.validade_cnh||'—'}</span></div><div class="actions"><button class="btn-outline" type="button" onclick="setView('documents')">Documentos</button></div>`;const docs=p.documents||{};$('docsList').innerHTML=Object.values(docs).map(d=>`<div class="detail-row"><span class="muted">${d.label||'Doc'}</span><span>${d.status} · upload ${d.upload_enabled?'ativo':'futuro'}</span></div>`).join('')}
async function loadNotifications(){const res=await api('/api/driver/notifications');if(!res.ok)return;$('notifList').innerHTML=(res.items||[]).map(n=>`<div class="notice ${n.lida?'':'unread'}"><strong>${n.titulo}</strong><br><span class="muted">${n.criado_em}</span><br>${n.mensagem}</div>`).join('')||'<p class="muted">Nenhum aviso.</p>'}
async function doLogout(){await api('/api/driver/logout');token='';sessionStorage.removeItem('driver_token');hide($('bottomNav'));hide($('logoutBtn'));setView('login')}
$('loginBtn').onclick=doLogin;$('logoutBtn').onclick=doLogout;document.querySelectorAll('#bottomNav button').forEach(b=>b.onclick=()=>{if(b.dataset.view==='agenda')loadReservations().then(()=>setView('agenda'));else if(b.dataset.view==='notifications')loadNotifications().then(()=>setView('notifications'));else if(b.dataset.view==='profile')loadProfile().then(()=>setView('profile'));else setView(b.dataset.view)});document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.filters button').forEach(x=>x.classList.remove('active'));b.classList.add('active');agendaFilter=b.dataset.filter;renderAgenda()});
if(token)bootApp();else setView('login');
</script>
</body>
</html>"""
