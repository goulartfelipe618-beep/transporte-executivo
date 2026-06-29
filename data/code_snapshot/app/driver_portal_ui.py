"""Interface web completa do Portal Motorista (mini painel operacional)."""
from __future__ import annotations

import json

from .driver_portal_access import activation_token_pending
from .driver_portal_dtos import portal_branding
from .driver_portal_panel import public_panel_config
from .portal_auth import driver_has_password


def render_driver_portal_page(app, driver, slug):
    branding = portal_branding(app)
    panel = public_panel_config(driver)
    empresa = panel.get("business_name") or branding["empresa"]
    logo_url = panel.get("logo_url") or branding.get("logo_url") or ""
    logo_inner = f'<img src="{logo_url}" alt="logo"/>' if logo_url else empresa[:1]
    activated = driver_has_password(driver)
    pending_token = activation_token_pending(driver)
    if activated:
        activation_msg = ""
    elif pending_token:
        activation_msg = "Primeiro acesso: informe seu CPF e cole o token de ativacao no campo Senha. Depois defina sua senha permanente."
    else:
        activation_msg = "Token ja utilizado ou expirado. Solicite um novo token ao administrador."
    html = _HTML.replace("__SLUG__", json.dumps(slug))
    html = html.replace("__ACTIVATED__", "true" if activated else "false")
    html = html.replace("__EMPRESA__", empresa)
    html = html.replace("__BUILD__", branding["build"])
    html = html.replace("__DRIVER_NOME__", driver.get("nome", "Motorista"))
    html = html.replace("__CPF_HINT__", driver.get("cpf", ""))
    html = html.replace("__LOGO_INNER__", logo_inner)
    html = html.replace("__ACTIVATION_MSG__", activation_msg)
    html = html.replace("__PRIMARY__", panel.get("primary_color") or "#2563eb")
    return html


_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="nexus-build" content="__BUILD__"/>
<title>Portal Motorista - __EMPRESA__</title>
<style>
:root{--sidebar:#111827;--sidebar2:#172033;--bg:#eef2f7;--panel:#ffffff;--panel2:#f8fafc;--text:#1f2937;--muted:#64748b;--line:#d9e2ef;--primary:__PRIMARY__;--primary2:#1d4ed8;--success:#15803d;--warning:#b45309;--danger:#b91c1c;--radius:12px;--shadow:0 14px 34px rgba(15,23,42,.10)}
*{box-sizing:border-box}html,body{margin:0;min-height:100%;font-family:"Segoe UI",Arial,sans-serif;background:var(--bg);color:var(--text)}button,a,input,select,textarea{font-family:inherit}.hidden{display:none!important}
.auth-shell{min-height:100vh;display:grid;place-items:center;padding:24px;background:linear-gradient(135deg,#111827 0%,#1f2937 54%,#334155 100%)}.login-wrap{width:100%;max-width:440px}.auth-card{background:#fff;border-radius:16px;box-shadow:0 22px 60px rgba(0,0,0,.28);padding:26px;border:1px solid rgba(255,255,255,.12)}.auth-brand{display:flex;gap:12px;align-items:center;margin-bottom:18px}.auth-brand .logo{width:48px;height:48px}.auth-card h1,.auth-card h2{margin:0 0 6px;font-size:1.35rem}.auth-card p{margin:0 0 14px;color:var(--muted);font-size:.9rem}
.app-shell{min-height:100vh;display:grid;grid-template-columns:280px 1fr}.sidebar{background:var(--sidebar);color:#cbd5e1;display:flex;flex-direction:column;min-height:100vh;box-shadow:6px 0 22px rgba(15,23,42,.16)}.sidebar-brand{padding:20px 18px;border-bottom:1px solid rgba(255,255,255,.08)}.brand-row{display:flex;gap:12px;align-items:center}.logo{width:44px;height:44px;border-radius:12px;background:#0f172a;border:1px solid rgba(255,255,255,.12);display:grid;place-items:center;overflow:hidden;font-weight:800;color:#fff;text-transform:uppercase}.logo img{width:100%;height:100%;object-fit:cover}.brand-title{font-weight:800;font-size:.93rem;color:#fff;letter-spacing:.03em;text-transform:uppercase}.brand-sub{font-size:.72rem;color:#94a3b8;margin-top:3px;text-transform:uppercase}.sidebar-nav{padding:14px 12px;display:flex;flex-direction:column;gap:5px;flex:1}.nav-link{width:100%;display:flex;align-items:center;gap:10px;background:transparent;border:0;color:#cbd5e1;text-decoration:none;border-radius:10px;padding:11px 12px;text-align:left;font-weight:700;font-size:.82rem;letter-spacing:.03em;text-transform:uppercase}.nav-link:hover{background:#1f2937;color:#fff}.nav-link.active{background:linear-gradient(90deg,var(--primary),var(--primary2));color:#fff;box-shadow:0 10px 24px rgba(37,99,235,.25)}.nav-icon{width:26px;height:26px;border-radius:7px;display:grid;place-items:center;background:rgba(255,255,255,.08);font-size:.78rem;color:#e2e8f0}.nav-link.active .nav-icon{background:rgba(255,255,255,.2);color:#fff}.sidebar-foot{padding:14px 18px;border-top:1px solid rgba(255,255,255,.08);font-size:.72rem;color:#94a3b8;display:flex;gap:8px;align-items:center;text-transform:uppercase}.status-dot{width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.14)}
.main-wrap{min-width:0;display:flex;flex-direction:column}.topbar{height:66px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 22px;box-shadow:0 1px 0 rgba(15,23,42,.03)}.topbar h1{margin:0;font-size:1.08rem;text-transform:uppercase;letter-spacing:.02em}.topbar-meta{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.chip{font-size:.75rem;padding:6px 10px;border-radius:999px;background:#eef2ff;color:#334155;border:1px solid #dbe3f5}.content{padding:20px;max-width:1320px;width:100%}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);margin-bottom:14px}.card h2,.card h3,.card h4{margin:0 0 12px}.muted{color:var(--muted);font-size:.86rem}.grid{display:grid;gap:14px}.grid-2{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-3{grid-template-columns:repeat(3,minmax(0,1fr))}.grid-4{grid-template-columns:repeat(4,minmax(0,1fr))}.stat{min-height:116px;display:flex;flex-direction:column;justify-content:space-between}.stat .lbl{color:var(--muted);font-size:.78rem;text-transform:uppercase;font-weight:700;letter-spacing:.04em}.stat .val{font-size:1.72rem;font-weight:800;color:var(--primary);line-height:1}.stat .sub{font-size:.78rem;color:var(--muted)}
label{display:block;font-size:.78rem;color:var(--muted);font-weight:700;text-transform:uppercase;margin:10px 0 6px}input,select,textarea{width:100%;padding:11px 12px;border-radius:10px;border:1px solid var(--line);background:#fff;color:var(--text);font-size:.92rem}textarea{min-height:92px;resize:vertical}input:focus,select:focus,textarea:focus{outline:2px solid rgba(37,99,235,.18);border-color:var(--primary)}
.btn,button.btn{background:var(--primary);color:#fff;border:1px solid var(--primary);border-radius:10px;padding:10px 13px;font-weight:800;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}.btn:hover{background:var(--primary2)}.btn-outline{background:#fff;color:#334155;border:1px solid var(--line);border-radius:10px;padding:10px 13px;font-weight:800;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center}.btn-outline:hover{border-color:var(--primary);color:var(--primary)}.btn-success,.btn-danger{border-radius:10px;padding:10px 13px;font-weight:800;cursor:pointer;border:1px solid transparent}.btn-success{background:var(--success);border-color:var(--success);color:#fff}.btn-danger{background:var(--danger);border-color:var(--danger);color:#fff}.btn-block{width:100%}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}.table{width:100%;border-collapse:collapse;background:#fff;font-size:.86rem}.table th{background:var(--panel2);color:#475569;text-transform:uppercase;font-size:.72rem;letter-spacing:.05em}.table th,.table td{padding:11px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.table tr:last-child td{border-bottom:0}.clickable{cursor:pointer}.clickable:hover td{background:#f8fafc}
.badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;font-size:.72rem;font-weight:800;background:#eef2f7;color:#475569}.badge.ok{background:#dcfce7;color:var(--success)}.badge.warn{background:#fef3c7;color:var(--warning)}.badge.err{background:#fee2e2;color:var(--danger)}.badge.mine{background:#dbeafe;color:#1d4ed8}.notice{border:1px solid var(--line);border-left:4px solid var(--primary);padding:11px 12px;border-radius:10px;background:#fff;margin-bottom:10px}.notice.unread{border-left-color:var(--warning);background:#fffaf0}.detail-row{display:grid;grid-template-columns:150px 1fr;gap:10px;margin-bottom:8px;font-size:.9rem}.alert{padding:10px 12px;border-radius:10px;margin-bottom:12px;font-size:.86rem;border:1px solid transparent}.alert.err{background:#fee2e2;color:#991b1b;border-color:#fecaca}.alert.ok{background:#dcfce7;color:#166534;border-color:#bbf7d0}.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.filters button{background:#fff;border:1px solid var(--line);border-radius:10px;padding:9px 12px;font-weight:800;color:#475569}.filters button.active{background:var(--primary);border-color:var(--primary);color:#fff}.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}.section-head h3{margin:0}
@media(max-width:920px){.app-shell{grid-template-columns:1fr}.sidebar{min-height:auto}.sidebar-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.sidebar-foot{display:none}.topbar{height:auto;padding:14px;align-items:flex-start;gap:12px;flex-direction:column}.content{padding:14px}.grid-2,.grid-3,.grid-4{grid-template-columns:1fr}.detail-row{grid-template-columns:1fr}.nav-link{font-size:.76rem}}
</style>
</head>
<body>
<div class="auth-shell" id="authShell">
  <section id="view-login" class="login-wrap">
    <div class="auth-card">
      <div class="auth-brand"><div class="logo">__LOGO_INNER__</div><div><h1>Portal Motorista</h1><p>__EMPRESA__</p></div></div>
      <p class="muted">Motorista: <strong>__DRIVER_NOME__</strong></p>
      <div id="loginAlert" class="alert err hidden"></div>
      <label for="cpf">CPF ou identificacao</label>
      <input id="cpf" inputmode="numeric" value="__CPF_HINT__"/>
      <label for="password">Senha</label>
      <input id="password" type="password" placeholder="Senha do portal ou token de ativacao"/>
      <button class="btn btn-block" id="loginBtn" type="button" style="margin-top:16px">Entrar</button>
      <p class="muted" style="margin-top:14px">__ACTIVATION_MSG__</p>
    </div>
  </section>
  <section id="view-set-password" class="login-wrap hidden">
    <div class="auth-card">
      <h2>Defina sua senha</h2>
      <p>Token validado. Crie uma senha permanente para acessar o portal.</p>
      <div id="setPasswordAlert" class="alert err hidden"></div>
      <label>Nova senha</label><input id="newPassword" type="password"/>
      <label>Repita a senha</label><input id="newPassword2" type="password"/>
      <button class="btn btn-block" id="setPasswordBtn" type="button" style="margin-top:16px">Salvar senha e continuar</button>
    </div>
  </section>
</div>
<div class="app-shell hidden" id="appShell">
  <aside class="sidebar">
    <div class="sidebar-brand">
      <div class="brand-row"><div class="logo">__LOGO_INNER__</div><div><div class="brand-title" id="brandTitle">__EMPRESA__</div><div class="brand-sub">Painel do motorista</div></div></div>
    </div>
    <nav class="sidebar-nav" id="sideNav">
      <button class="nav-link" type="button" data-view="dashboard"><span class="nav-icon">D</span><span>Dashboard</span></button>
      <button class="nav-link" type="button" data-view="reservations"><span class="nav-icon">R</span><span>Reservas</span></button>
      <button class="nav-link" type="button" data-view="clients"><span class="nav-icon">C</span><span>Clientes</span></button>
      <button class="nav-link" type="button" data-view="finance"><span class="nav-icon">F</span><span>Financeiro</span></button>
      <button class="nav-link" type="button" data-view="notifications"><span class="nav-icon">A</span><span>Avisos</span></button>
      <button class="nav-link" type="button" data-view="profile"><span class="nav-icon">P</span><span>Perfil</span></button>
      <button class="nav-link" type="button" data-view="settings"><span class="nav-icon">S</span><span>Ajustes</span></button>
    </nav>
    <div class="sidebar-foot"><div class="status-dot"></div><span>Online - Build __BUILD__</span></div>
  </aside>
  <div class="main-wrap">
    <header class="topbar">
      <h1 id="pageTitle">Dashboard</h1>
      <div class="topbar-meta"><span class="chip">__DRIVER_NOME__</span><span class="chip">Build __BUILD__</span><button class="btn-outline" id="logoutBtn" type="button">Sair</button></div>
    </header>
    <main class="content">
      <section id="view-dashboard" class="hidden">
        <div class="grid grid-4">
          <div class="card stat"><div class="lbl">Reservas hoje</div><div class="val" id="cardHoje">0</div><div class="sub">Agenda do dia</div></div>
          <div class="card stat"><div class="lbl">Proximas</div><div class="val" id="cardProximas">0</div><div class="sub">Ate 7 dias</div></div>
          <div class="card stat"><div class="lbl">Minhas reservas</div><div class="val" id="cardMinhas">0</div><div class="sub">Criadas no portal</div></div>
          <div class="card stat"><div class="lbl">Atribuidas</div><div class="val" id="cardAtribuidas">0</div><div class="sub">Operacao Master</div></div>
        </div>
        <div class="grid grid-2">
          <div class="card"><div class="section-head"><h3>Proximas reservas</h3><button class="btn-outline" type="button" onclick="setView('reservations')">Ver agenda</button></div><div id="dashList"></div></div>
          <div class="card"><h3>Resumo operacional</h3><div id="dashIndicators"></div></div>
        </div>
      </section>
      <section id="view-reservations" class="hidden">
        <div class="card">
          <div class="section-head"><h3>Reservas</h3><button class="btn" type="button" onclick="setView('reservation-form')">Nova reserva</button></div>
          <div class="filters"><button type="button" class="active" data-filter="all">Todas</button><button type="button" data-filter="mine">Minhas</button><button type="button" data-filter="assigned">Atribuidas</button><button type="button" data-filter="today">Hoje</button><button type="button" data-filter="week">Semana</button></div>
          <div class="table-wrap"><table class="table"><thead><tr><th>Origem</th><th>Cliente</th><th>Data</th><th>Trajeto</th><th>Status</th></tr></thead><tbody id="agendaBody"></tbody></table></div>
        </div>
      </section>
      <section id="view-reservation-form" class="hidden">
        <div class="card"><h3>Nova reserva propria</h3><div id="reservationAlert" class="alert hidden"></div><div class="grid grid-2"><div><label>Cliente salvo</label><select id="resClient"><option value="">Cadastrar/informar manualmente</option></select></div><div><label>Tipo cliente</label><select id="resTipoCliente"><option value="fisica">Pessoa fisica</option><option value="juridica">Empresa</option></select></div><div><label>Nome / Razao social</label><input id="resCliente"/></div><div><label>Documento</label><input id="resDocumento"/></div><div><label>Telefone</label><input id="resTelefone"/></div><div><label>Email</label><input id="resEmail"/></div><div><label>Origem</label><input id="resOrigem"/></div><div><label>Destino</label><input id="resDestino"/></div><div><label>Data</label><input id="resData" placeholder="dd/mm/aaaa"/></div><div><label>Hora</label><input id="resHora" placeholder="08:00"/></div><div><label>Passageiros</label><input id="resPassageiros" value="1"/></div><div><label>Valor</label><input id="resValor" placeholder="R$ 0,00"/></div></div><label>Observacoes</label><textarea id="resObs"></textarea><div class="actions"><button class="btn" type="button" onclick="createReservation()">Salvar reserva</button><button class="btn-outline" type="button" onclick="setView('reservations')">Cancelar</button></div></div>
      </section>
      <section id="view-detail" class="hidden"><div class="card" id="detailCard"></div></section>
      <section id="view-clients" class="hidden">
        <div class="grid grid-2"><div class="card"><h3>Novo cliente centralizado</h3><div id="clientAlert" class="alert hidden"></div><label>Tipo</label><select id="clientTipo"><option value="fisica">Pessoa fisica</option><option value="juridica">Empresa</option></select><label>Nome / Razao social</label><input id="clientNome"/><label>Nome fantasia / Responsavel</label><input id="clientFantasia"/><label>CPF/CNPJ</label><input id="clientDocumento"/><label>Telefone</label><input id="clientTelefone"/><label>Email</label><input id="clientEmail"/><button class="btn btn-block" type="button" style="margin-top:12px" onclick="createClient()">Cadastrar cliente</button></div><div class="card"><h3>Meus clientes</h3><div id="clientsList"></div></div></div>
      </section>
      <section id="view-finance" class="hidden">
        <div class="grid grid-4">
          <div class="card stat"><div class="lbl">Receita propria</div><div class="val" id="finReceita">R$ 0,00</div><div class="sub">Reservas criadas por voce</div></div>
          <div class="card stat"><div class="lbl">Repasse atribuido</div><div class="val" id="finRepasse">R$ 0,00</div><div class="sub">Servicos da operacao</div></div>
          <div class="card stat"><div class="lbl">Em aberto</div><div class="val" id="finAberto">R$ 0,00</div><div class="sub">Previsto nao finalizado</div></div>
          <div class="card stat"><div class="lbl">Concluido</div><div class="val" id="finConcluido">R$ 0,00</div><div class="sub">Viagens concluidas</div></div>
        </div>
        <div class="card"><div class="section-head"><h3>Movimento financeiro</h3><button class="btn-outline" type="button" onclick="loadFinance()">Atualizar</button></div><div class="table-wrap"><table class="table"><thead><tr><th>Tipo</th><th>Reserva</th><th>Cliente</th><th>Data</th><th>Status</th><th>Valor</th></tr></thead><tbody id="financeBody"></tbody></table></div><p class="muted">Valores atribuidos respeitam a configuracao de ocultacao definida pela operacao.</p></div>
      </section>
      <section id="view-notifications" class="hidden"><div class="card"><h3>Avisos</h3><div id="notifList"></div></div></section>
      <section id="view-profile" class="hidden"><div class="card" id="profileCard"></div></section>
      <section id="view-settings" class="hidden"><div class="grid grid-2"><div class="card"><h3>Identidade do mini painel</h3><div id="settingsAlert" class="alert hidden"></div><label>Nome comercial</label><input id="setBusiness"/><label>Logo (URL publica)</label><input id="setLogo" placeholder="https://.../logo.png"/><label>Cor principal</label><input id="setColor" placeholder="#2563eb"/><label>Contrato para aparecer no slip/PDF</label><textarea id="setContract"></textarea><label>Codigo 2FA (se ativo)</label><input id="setTotpCode" inputmode="numeric" maxlength="6"/><button class="btn btn-block" type="button" style="margin-top:12px" onclick="saveSettings()">Salvar configuracoes</button></div><div class="card"><h3>Seguranca 2FA</h3><p class="muted" id="totpStatus">Carregando...</p><div id="totpSetupBox"></div><div class="actions"><button class="btn-outline" type="button" onclick="setupTotp()">Configurar 2FA</button><button class="btn-danger" type="button" onclick="disableTotp()">Desativar 2FA</button></div></div></div></section>
    </main>
  </div>
</div>
<script>
const SLUG=__SLUG__;const VIEW_TITLES={dashboard:'Dashboard',reservations:'Reservas',clients:'Clientes',finance:'Financeiro',notifications:'Avisos',profile:'Perfil',settings:'Ajustes','reservation-form':'Nova reserva',detail:'Detalhe da reserva'};let token=sessionStorage.getItem('driver_token')||'';let reservations=[];let clients=[];let filter='all';let settings={};
function $(id){return document.getElementById(id)}function show(el){if(el)el.classList.remove('hidden')}function hide(el){if(el)el.classList.add('hidden')}function msg(id,text,ok=false){const el=$(id);el.className='alert '+(ok?'ok':'err');el.textContent=text;show(el)}
async function api(path,body={}){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:SLUG,token,...body})});return r.json()}
function showAuth(name){hide($('appShell'));show($('authShell'));['login','set-password'].forEach(v=>hide($('view-'+v)));show($('view-'+name))}
function setView(name){hide($('authShell'));show($('appShell'));['dashboard','reservations','reservation-form','detail','clients','finance','notifications','profile','settings'].forEach(v=>hide($('view-'+v)));show($('view-'+name));$('pageTitle').textContent=VIEW_TITLES[name]||'Portal';document.querySelectorAll('#sideNav button').forEach(b=>b.classList.toggle('active',b.dataset.view===name));if(name==='reservations')loadReservations();if(name==='clients')loadClients();if(name==='finance')loadFinance();if(name==='settings')loadSettings();if(name==='notifications')loadNotifications();if(name==='profile')loadProfile()}
function statusBadge(s){const v=(s||'').toLowerCase();let c='badge';if(v.includes('conclu'))c+=' ok';else if(v.includes('cancel'))c+=' err';else if(v.includes('pend')||v.includes('aceitar'))c+=' warn';return `<span class="${c}">${s||'-'}</span>`}
async function doLogin(){hide($('loginAlert'));const res=await fetch('/api/driver/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:SLUG,cpf:$('cpf').value,identificacao:$('cpf').value,password:$('password').value})}).then(r=>r.json());if(!res.ok){msg('loginAlert','CPF ou token/senha invalidos.');return}token=res.token;sessionStorage.setItem('driver_token',token);if(res.requires_password_setup){sessionStorage.setItem('driver_pending_password','1');showAuth('set-password');return}sessionStorage.removeItem('driver_pending_password');await bootApp()}
async function doSetPassword(){hide($('setPasswordAlert'));const p1=$('newPassword').value,p2=$('newPassword2').value;if(p1.length<6)return msg('setPasswordAlert','Senha deve ter pelo menos 6 caracteres.');if(p1!==p2)return msg('setPasswordAlert','As senhas nao conferem.');const res=await api('/api/driver/set-password',{password:p1,password_confirm:p2});if(!res.ok)return msg('setPasswordAlert','Nao foi possivel salvar a senha.');sessionStorage.removeItem('driver_pending_password');await bootApp()}
async function bootApp(){if(!token){showAuth('login');return}if(sessionStorage.getItem('driver_pending_password')==='1'){showAuth('set-password');return}const dash=await api('/api/driver/dashboard');if(!dash.ok){token='';sessionStorage.clear();showAuth('login');return}renderDashboard(dash);await Promise.all([loadReservations(),loadClients(),loadSettings(),loadProfile(),loadNotifications(),loadFinance()]);setView('dashboard')}
function renderDashboard(d){$('cardHoje').textContent=d.cards.hoje;$('cardProximas').textContent=d.cards.proximas;$('cardMinhas').textContent=d.cards.minhas||0;$('cardAtribuidas').textContent=d.cards.atribuidas||0;$('dashList').innerHTML=(d.proximas_reservas||[]).map(r=>`<div class="notice clickable" onclick="openDetail('${r.numero}')"><strong>${r.numero}</strong> <span class="badge ${r.owned_by_driver?'mine':''}">${r.source_label}</span><br>${r.data} ${r.hora||''} - ${r.origem} para ${r.destino} ${statusBadge(r.status)}</div>`).join('')||'<p class="muted">Nenhuma reserva proxima.</p>';$('dashIndicators').innerHTML=`<div class="detail-row"><span class="muted">Status do portal</span><span>${d.indicators.portal_status||'-'}</span></div><div class="detail-row"><span class="muted">Ultimo acesso</span><span>${d.indicators.ultimo_acesso||'-'}</span></div><div class="detail-row"><span class="muted">Cidade base</span><span>${d.indicators.cidade_principal||'-'} / ${d.indicators.estado||'-'}</span></div><div class="detail-row"><span class="muted">Pendentes</span><span>${d.cards.pendentes||0}</span></div>`}
async function loadReservations(){const res=await api('/api/driver/reservations');if(res.ok)reservations=res.items||[];renderReservations();fillClientSelect()}
function passFilter(r){if(filter==='mine')return r.owned_by_driver;if(filter==='assigned')return !r.owned_by_driver;const d=parseDate(r.data);const today=new Date();today.setHours(0,0,0,0);if(filter==='today')return d&&d.getTime()===today.getTime();if(filter==='week'){const w=new Date(today);w.setDate(w.getDate()+7);return d&&d>=today&&d<=w}return true}
function parseDate(s){if(!s)return null;const p=String(s).slice(0,10).split('/');if(p.length===3)return new Date(+p[2],+p[1]-1,+p[0]);return null}
function renderReservations(){const rows=reservations.filter(passFilter);$('agendaBody').innerHTML=rows.map(r=>`<tr class="clickable" onclick="openDetail('${r.numero}')"><td><span class="badge ${r.owned_by_driver?'mine':''}">${r.source_label}</span></td><td>${r.cliente||'-'}</td><td>${r.data||'-'} ${r.hora||''}</td><td>${r.origem||'-'} para ${r.destino||'-'}</td><td>${statusBadge(r.status)}</td></tr>`).join('')||'<tr><td colspan="5" class="muted">Sem reservas.</td></tr>'}
async function openDetail(numero){const res=await api('/api/driver/reservation',{numero});if(!res.ok)return alert('Reserva nao permitida.');const r=res.item;let edit=r.can_edit?`<h4>Editar minha reserva</h4><div class="grid grid-2"><input id="editOrigem" value="${r.origem||''}"/><input id="editDestino" value="${r.destino||''}"/><input id="editData" value="${r.data||''}"/><input id="editHora" value="${r.hora||''}"/></div><label>Observacoes</label><textarea id="editObs">${r.observacoes||''}</textarea><label>2FA se ativo</label><input id="editTotp" maxlength="6"/><div class="actions"><button class="btn" onclick="updateReservation('${r.numero}')">Salvar edicao</button><button class="btn-danger" onclick="cancelReservation('${r.numero}')">Cancelar reserva</button></div>`:'';$('detailCard').innerHTML=`<h3>Reserva ${r.numero} <span class="badge ${r.owned_by_driver?'mine':''}">${r.source_label}</span></h3><div class="detail-row"><span class="muted">Cliente</span><span>${r.cliente||'-'}</span></div><div class="detail-row"><span class="muted">Data/Hora</span><span>${r.data||'-'} ${r.hora||''}</span></div><div class="detail-row"><span class="muted">Origem</span><span>${r.origem||'-'}</span></div><div class="detail-row"><span class="muted">Destino</span><span>${r.destino||'-'}</span></div><div class="detail-row"><span class="muted">Status</span><span>${statusBadge(r.status)}</span></div><p class="muted">${r.observacoes||''}</p><div class="actions"><a class="btn-outline" href="${r.maps_url}" target="_blank">Abrir rota</a><button class="btn-outline" onclick="downloadPdf('${r.numero}','cliente')">PDF Cliente</button><button class="btn-outline" onclick="downloadPdf('${r.numero}','motorista')">PDF Motorista</button></div><div class="actions" id="statusActions"></div>${edit}`;(res.actions||[]).forEach(a=>{const b=document.createElement('button');b.className='btn btn-success';b.textContent=a.label;b.onclick=()=>updateStatus(r.numero,a.status);$('statusActions').appendChild(b)});setView('detail')}
async function updateStatus(numero,status){const res=await api('/api/driver/status',{numero,status});if(!res.ok)return alert('Sem permissao.');await loadReservations();await loadFinance();openDetail(numero)}
async function updateReservation(numero){const res=await api('/api/driver/reservation-update',{numero,origem:$('editOrigem').value,destino:$('editDestino').value,data:$('editData').value,hora:$('editHora').value,observacoes:$('editObs').value,totp_code:$('editTotp').value});if(!res.ok)return alert(res.error||'Erro');await loadReservations();await loadFinance();openDetail(numero)}
async function cancelReservation(numero){if(!confirm('Cancelar esta reserva propria?'))return;const res=await api('/api/driver/reservation-cancel',{numero,totp_code:$('editTotp').value});if(!res.ok)return alert(res.error||'Erro');await loadReservations();await loadFinance();openDetail(numero)}
async function createReservation(){const payload={client_id:$('resClient').value,tipo_cliente:$('resTipoCliente').value,cliente:$('resCliente').value,documento:$('resDocumento').value,telefone:$('resTelefone').value,email:$('resEmail').value,origem:$('resOrigem').value,destino:$('resDestino').value,data:$('resData').value,hora:$('resHora').value,passageiros:$('resPassageiros').value,valor:$('resValor').value,observacoes:$('resObs').value};const res=await api('/api/driver/reservation-create',payload);if(!res.ok)return msg('reservationAlert',res.error||'Erro ao salvar.');msg('reservationAlert','Reserva criada com sucesso.',true);await loadReservations();await loadFinance();setView('reservations')}
async function downloadPdf(numero,via){const res=await api('/api/driver/reservation-pdf',{numero,via});if(!res.ok)return alert(res.error||'Erro PDF');const bin=atob(res.content_base64);const bytes=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);const blob=new Blob([bytes],{type:res.mime});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=res.filename;a.click();URL.revokeObjectURL(a.href)}
async function loadClients(){const res=await api('/api/driver/clients');if(res.ok)clients=res.items||[];$('clientsList').innerHTML=clients.map(c=>`<div class="notice"><strong>${c.nome}</strong> <span class="badge">${c.tipo_pessoa}</span><br><span class="muted">${c.documento||'-'} - ${c.telefone||'-'} - ${c.email||'-'}</span></div>`).join('')||'<p class="muted">Nenhum cliente cadastrado por voce.</p>';fillClientSelect()}
function fillClientSelect(){const sel=$('resClient');if(!sel)return;const cur=sel.value;sel.innerHTML='<option value="">Cadastrar/informar manualmente</option>'+clients.map(c=>`<option value="${c.id}">${c.tipo_pessoa==='juridica'?'[Empresa]':'[PF]'} ${c.nome}</option>`).join('');sel.value=cur}
async function createClient(){const payload={tipo_pessoa:$('clientTipo').value,nome:$('clientNome').value,nome_fantasia:$('clientFantasia').value,razao_social:$('clientNome').value,responsavel:$('clientFantasia').value,documento:$('clientDocumento').value,telefone:$('clientTelefone').value,email:$('clientEmail').value};const res=await api('/api/driver/client-create',payload);if(!res.ok)return msg('clientAlert',res.error||'Erro ao cadastrar cliente.');msg('clientAlert','Cliente cadastrado no cadastro central.',true);['clientNome','clientFantasia','clientDocumento','clientTelefone','clientEmail'].forEach(id=>$(id).value='');await loadClients()}
async function loadFinance(){const res=await api('/api/driver/finance');if(!res.ok)return;const c=res.cards||{};$('finReceita').textContent=c.receita_propria||'R$ 0,00';$('finRepasse').textContent=c.repasse_atribuido||'R$ 0,00';$('finAberto').textContent=c.em_aberto||'R$ 0,00';$('finConcluido').textContent=c.concluido||'R$ 0,00';$('financeBody').innerHTML=(res.items||[]).map(r=>`<tr class="clickable" onclick="openDetail('${r.numero}')"><td><span class="badge ${r.owned_by_driver?'mine':''}">${r.tipo}</span></td><td>${r.numero||'-'}</td><td>${r.cliente||'-'}</td><td>${r.data||'-'}</td><td>${statusBadge(r.status)}</td><td>${r.valor||'-'}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">Sem movimento financeiro.</td></tr>'}
async function loadProfile(){const res=await api('/api/driver/profile');if(!res.ok)return;const p=res.profile;$('profileCard').innerHTML=`<h3>${p.nome}</h3><div class="detail-row"><span class="muted">CPF</span><span>${p.cpf_masked||p.cpf||'-'}</span></div><div class="detail-row"><span class="muted">Telefone</span><span>${p.telefone||'-'}</span></div><div class="detail-row"><span class="muted">Email</span><span>${p.email||'-'}</span></div><div class="detail-row"><span class="muted">Cidade/UF</span><span>${p.cidade||'-'} / ${p.estado||'-'}</span></div><div class="detail-row"><span class="muted">CNH</span><span>${p.validade_cnh||'-'}</span></div>`}
async function loadNotifications(){const res=await api('/api/driver/notifications');if(!res.ok)return;$('notifList').innerHTML=(res.items||[]).map(n=>`<div class="notice ${n.lida?'':'unread'}"><strong>${n.titulo}</strong><br><span class="muted">${n.criado_em}</span><br>${n.mensagem}</div>`).join('')||'<p class="muted">Nenhum aviso.</p>'}
async function loadSettings(){const res=await api('/api/driver/settings');if(!res.ok)return;settings=res.settings;$('setBusiness').value=settings.business_name||'';$('setLogo').value=settings.logo_url||'';$('setColor').value=settings.primary_color||'#2563eb';$('setContract').value=settings.contract_text||'';$('totpStatus').textContent=settings.totp_enabled?'2FA ativo para alteracoes sensiveis.':'2FA inativo.'}
async function saveSettings(){const res=await api('/api/driver/settings-save',{business_name:$('setBusiness').value,logo_url:$('setLogo').value,primary_color:$('setColor').value,contract_text:$('setContract').value,totp_code:$('setTotpCode').value});if(!res.ok)return msg('settingsAlert',res.error||'Erro ao salvar.');msg('settingsAlert','Configuracoes salvas.',true);$('brandTitle').textContent=res.settings.business_name||$('brandTitle').textContent;await loadSettings()}
async function setupTotp(){const res=await api('/api/driver/totp-setup');if(!res.ok)return;$('totpSetupBox').innerHTML=`<p class="muted">Escaneie o QR Code e digite o codigo para ativar.</p><img alt="QR 2FA" src="${res.qr}" style="max-width:180px;background:white;padding:8px;border-radius:8px"/><label>Codigo 2FA</label><input id="totpEnableCode" maxlength="6"/><button class="btn btn-block" onclick="enableTotp()">Ativar 2FA</button>`}
async function enableTotp(){const res=await api('/api/driver/totp-enable',{totp_code:$('totpEnableCode').value});if(!res.ok)return alert(res.error||'Codigo invalido');await loadSettings();$('totpSetupBox').innerHTML=''}
async function disableTotp(){const code=prompt('Codigo 2FA atual');if(code===null)return;const res=await api('/api/driver/totp-disable',{totp_code:code});if(!res.ok)return alert(res.error||'Erro');await loadSettings()}
async function doLogout(){await api('/api/driver/logout');token='';sessionStorage.clear();showAuth('login')}
$('loginBtn').onclick=doLogin;$('setPasswordBtn').onclick=doSetPassword;$('logoutBtn').onclick=doLogout;document.querySelectorAll('#sideNav button').forEach(b=>b.onclick=()=>setView(b.dataset.view));document.querySelectorAll('.filters button[data-filter]').forEach(b=>b.onclick=()=>{document.querySelectorAll('.filters button[data-filter]').forEach(x=>x.classList.remove('active'));b.classList.add('active');filter=b.dataset.filter;renderReservations()});
if(token&&sessionStorage.getItem('driver_pending_password')==='1')showAuth('set-password');else if(token)bootApp();else showAuth('login');
</script>
</body>
</html>"""
