"""Interface web completa do Portal Empresa."""
from __future__ import annotations

import json

from .settings_store import load_settings
from .version import APP_BUILD


def render_company_portal_page(slug, company_name):
    settings = load_settings()
    empresa = settings.get("nome_projeto") or settings.get("empresa") or "Nexus Transfer"
    html = _HTML.replace("__SLUG__", json.dumps(slug))
    html = html.replace("__EMPRESA__", empresa)
    html = html.replace("__COMPANY_NAME__", company_name)
    html = html.replace("__BUILD__", APP_BUILD)
    return html


_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Portal Empresa — __COMPANY_NAME__</title>
<style>
:root{--bg:#eef2f7;--panel:#fff;--primary:#2563eb;--text:#0f172a;--muted:#64748b;--line:#e2e8f0;--ok:#16a34a;--warn:#d97706;--err:#dc2626}
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:var(--bg);color:var(--text)}
.hidden{display:none!important}.wrap{max-width:1200px;margin:0 auto;padding:16px;padding-bottom:90px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:14px;box-shadow:0 4px 18px rgba(15,23,42,.05)}
.top{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.top h1{margin:0;font-size:1.1rem}.muted{color:var(--muted);font-size:.85rem}
.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(4,1fr)}.g2{grid-template-columns:repeat(2,1fr)}@media(max-width:900px){.g4,.g2{grid-template-columns:1fr 1fr}}@media(max-width:560px){.g4,.g2{grid-template-columns:1fr}}
.stat{background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:14px;text-align:center}.stat b{display:block;font-size:1.5rem;margin-top:4px;color:var(--primary)}
nav.topnav{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}nav.topnav button,button.btn{padding:9px 12px;border-radius:10px;border:1px solid var(--line);background:#fff;color:var(--text);cursor:pointer;font-size:.82rem}
button.btn.primary{background:var(--primary);color:#fff;border-color:var(--primary)}button.btn.danger{background:var(--err);color:#fff;border-color:var(--err)}
input,select,textarea{width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;margin:6px 0 12px}label{font-size:.82rem;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:.85rem}th,td{border-bottom:1px solid var(--line);padding:9px;text-align:left;vertical-align:top}
.bottomnav{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);display:flex;justify-content:space-around;padding:8px;z-index:20}
.bottomnav button{background:none;border:0;font-size:.72rem;color:var(--muted);display:flex;flex-direction:column;align-items:center;gap:3px;padding:6px}
.bottomnav button.active{color:var(--primary)}.error{color:var(--err);font-size:.82rem}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:700px){.row{grid-template-columns:1fr}}
</style></head><body>
<div class="wrap">
<div id="loginView" class="card"><h1>Portal da Empresa</h1><p class="muted">__COMPANY_NAME__ · __EMPRESA__ · Build __BUILD__</p>
<label>Email</label><input id="loginEmail" type="email"/><label>Senha</label><input id="loginPassword" type="password"/>
<p id="loginError" class="error"></p><button class="btn primary" onclick="login()">Entrar</button></div>
<div id="appView" class="hidden">
<div class="card top"><div><h1 id="companyTitle">__COMPANY_NAME__</h1><p class="muted" id="userLine"></p></div><div style="flex:1"></div><button class="btn" onclick="logout()">Sair</button></div>
<nav class="topnav" id="mainNav"></nav>
<div id="views"></div>
</div></div>
<nav class="bottomnav hidden" id="bottomNav"></nav>
<script>
const slug=__SLUG__;let token=localStorage.getItem('corpToken_'+slug)||'';let permissions=[];let user={};let costCenters=[];let passengers=[];
const NAV=[
  {id:'dashboard',label:'Dashboard',perm:'dashboard',icon:'⌂'},
  {id:'history',label:'Historico',perm:'history',icon:'📋'},
  {id:'request',label:'Nova Solicitacao',perm:'request',icon:'➕'},
  {id:'approval',label:'Aprovacoes',perm:'approve',icon:'✓'},
  {id:'passengers',label:'Passageiros',perm:'passengers',icon:'👥'},
  {id:'cost_centers',label:'Centros de Custo',perm:'cost_centers',icon:'🏷'},
  {id:'users',label:'Usuarios',perm:'users',icon:'🔐'},
  {id:'finance',label:'Financeiro',perm:'finance',icon:'💰'},
  {id:'calculator',label:'Calculadora',perm:'calculator',icon:'🧮'},
  {id:'catalog',label:'Catalogo',perm:'vehicles',icon:'🚗'},
];
function api(path,body){return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,slug,token})}).then(r=>r.json())}
function can(p){return permissions.includes(p)}
function login(){api('/api/company/login',{email:loginEmail.value,password:loginPassword.value}).then(d=>{if(!d.ok){loginError.textContent=d.error||'Login invalido';return}token=d.token;permissions=d.permissions||[];user=d.user||{};localStorage.setItem('corpToken_'+slug,token);boot()})}
function logout(){api('/api/company/logout',{}).finally(()=>{token='';permissions=[];localStorage.removeItem('corpToken_'+slug);loginView.classList.remove('hidden');appView.classList.add('hidden');bottomNav.classList.add('hidden')})}
function renderNav(){const items=NAV.filter(n=>can(n.perm));mainNav.innerHTML=items.map(n=>`<button onclick="show('${n.id}')">${n.label}</button>`).join('');bottomNav.innerHTML=items.slice(0,4).map(n=>`<button data-v="${n.id}" onclick="show('${n.id}')"><span>${n.icon}</span>${n.label}</button>`).join('')}
function show(id){document.querySelectorAll('#bottomNav button').forEach(b=>b.classList.toggle('active',b.dataset.v===id));({dashboard:loadDashboard,history:loadHistory,request:loadRequest,approval:loadApproval,passengers:loadPassengers,cost_centers:loadCostCenters,users:loadUsers,finance:loadFinance,calculator:loadCalculator,catalog:loadCatalog})[id]?.()}
function boot(){api('/api/company/dashboard',{}).then(d=>{if(!d.ok)return logout();permissions=d.permissions||permissions;user=d.user||user;companyTitle.textContent=d.company?.nome||companyTitle.textContent;userLine.textContent=(user.perfil||'')+' · '+ (user.nome||'');loginView.classList.add('hidden');appView.classList.remove('hidden');bottomNav.classList.remove('hidden');renderNav();loadDashboard()})}
function card(title,inner){views.innerHTML=`<div class="card"><h2 style="margin:0 0 12px">${title}</h2>${inner}</div>`}
function table(headers,rows){if(!rows.length)return '<p class="muted">Nenhum registro.</p>';return '<table><thead><tr>'+headers.map(h=>`<th>${h}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(c=>`<td>${c??''}</td>`).join('')+'</tr>').join('')+'</tbody></table>'}
async function loadDashboard(){const d=await api('/api/company/dashboard',{});const s=d.stats||{};card('Dashboard corporativo',`<div class="grid g4">
<div class="stat"><span class="muted">Em aberto</span><b>${s.open??0}</b></div><div class="stat"><span class="muted">Em andamento</span><b>${s.in_progress??0}</b></div>
<div class="stat"><span class="muted">Concluidas</span><b>${s.done??0}</b></div><div class="stat"><span class="muted">Canceladas</span><b>${s.cancelled??0}</b></div></div>
<h3>Indicadores</h3><p class="muted">Usuarios ativos: ${s.indicators?.usuarios_ativos??0} · Centros de custo: ${s.indicators?.centros_custo??0} · Passageiros: ${s.indicators?.passageiros??0}</p>
<h3>Ultimas atividades</h3>${(d.activity||[]).map(a=>`<p>${a}</p>`).join('')||'<p class="muted">Sem movimentacao.</p>'}`)}
async function loadHistory(){const status=historyStatus?.value||'';const cc=historyCc?.value||'';const df=historyFrom?.value||'';const dt=historyTo?.value||'';const page=historyPage||1;
card('Historico',`<div class="row"><div><label>Status</label><input id="historyStatus" value="${status}"/></div><div><label>Centro de custo ID</label><input id="historyCc" value="${cc}"/></div></div>
<div class="row"><div><label>De (DD/MM/AAAA)</label><input id="historyFrom" value="${df}"/></div><div><label>Ate</label><input id="historyTo" value="${dt}"/></div></div>
<button class="btn primary" onclick="loadHistory()">Filtrar</button><div id="historyTable"></div>`);
const d=await api('/api/company/history',{status:document.getElementById('historyStatus')?.value||'',centro_custo_id:document.getElementById('historyCc')?.value||'',date_from:document.getElementById('historyFrom')?.value||'',date_to:document.getElementById('historyTo')?.value||'',page:1,per_page:20});
historyTable.innerHTML=table(['Tipo','Ref','Data','Status','Centro de custo'],(d.items||[]).map(i=>[i.tipo,i.numero||i.id,i.data||i.criado_em,i.status,i.centro_custo_nome]))+`<p class="muted">Pagina ${d.page}/${d.pages} · Total ${d.total}</p>`}
async function loadRequest(){await api('/api/company/cost-centers/list',{}).then(d=>costCenters=d.items||[]);await api('/api/company/passengers/list',{}).then(d=>passengers=d.items||[]);
card('Nova solicitacao',`<div class="row"><div><label>Origem</label><input id="reqOrigem"/></div><div><label>Destino</label><input id="reqDestino"/></div></div>
<div class="row"><div><label>Data</label><input id="reqData" placeholder="DD/MM/AAAA"/></div><div><label>Hora</label><input id="reqHora"/></div></div>
<label>Passageiros</label><input id="reqPassageiros" type="number" min="1" value="1"/>
<label>Categoria</label><select id="reqCategoria"><option>Sedan</option><option>SUV</option><option>Van</option><option>Executivo</option></select>
<label>Centro de custo</label><select id="reqCc">${costCenters.map(c=>`<option value="${c.id}">${c.codigo} - ${c.nome}</option>`).join('')}</select>
<button class="btn primary" onclick="submitRequest()">Enviar</button><p id="reqMsg" class="muted"></p>`)}
function submitRequest(){api('/api/company/request',{origem:reqOrigem.value,destino:reqDestino.value,data:reqData.value,hora:reqHora.value,passageiros:reqPassageiros.value,categoria:reqCategoria.value,centro_custo_id:reqCc?.value||''}).then(d=>{reqMsg.textContent=d.ok?(d.approval_required?'Enviado para aprovacao.':'Solicitacao registrada.'):(d.error||'Falha')})}
async function loadApproval(){const d=await api('/api/company/approvals/list',{});card('Fluxo de aprovacao',table(['ID','Origem','Destino','Status','Acao'],(d.items||[]).map(i=>[i.id,i.origem,i.destino,i.approval_status||i.status,`<button class="btn primary" onclick="approve('${i.id}')">Aprovar</button> <button class="btn danger" onclick="reject('${i.id}')">Rejeitar</button>`])))}
function approve(id){api('/api/company/approve',{request_id:id}).then(()=>loadApproval())}
function reject(id){api('/api/company/reject',{request_id:id}).then(()=>loadApproval())}
async function loadPassengers(){card('Passageiros',`<div class="row"><div><label>Nome</label><input id="psgNome"/></div><div><label>CPF</label><input id="psgCpf"/></div></div>
<div class="row"><div><label>Telefone</label><input id="psgTel"/></div><div><label>Email</label><input id="psgEmail"/></div></div>
<label>Observacoes</label><textarea id="psgObs"></textarea><button class="btn primary" onclick="savePassenger()">Salvar</button><div id="psgList"></div>`);const d=await api('/api/company/passengers/list',{});psgList.innerHTML=table(['Nome','CPF','Telefone','Email'],(d.items||[]).map(p=>[p.nome,p.cpf,p.telefone,p.email]))}
function savePassenger(){api('/api/company/passengers/save',{nome:psgNome.value,cpf:psgCpf.value,telefone:psgTel.value,email:psgEmail.value,observacoes:psgObs.value}).then(()=>loadPassengers())}
async function loadCostCenters(){card('Centros de Custo',`<div class="row"><div><label>Codigo</label><input id="ccCodigo"/></div><div><label>Nome</label><input id="ccNome"/></div></div>
<button class="btn primary" onclick="saveCc()">Salvar</button><div id="ccList"></div>`);const d=await api('/api/company/cost-centers/list',{});ccList.innerHTML=table(['Codigo','Nome','Status'],(d.items||[]).map(c=>[c.codigo,c.nome,c.status]))}
function saveCc(){api('/api/company/cost-centers/save',{codigo:ccCodigo.value,nome:ccNome.value}).then(()=>loadCostCenters())}
async function loadUsers(){card('Usuarios corporativos',`<div class="row"><div><label>Nome</label><input id="usrNome"/></div><div><label>Email</label><input id="usrEmail"/></div></div>
<div class="row"><div><label>Perfil</label><select id="usrPerfil"><option>Solicitante</option><option>Gestor</option><option>Financeiro</option><option>Administrador da Empresa</option></select></div><div><label>Senha</label><input id="usrSenha" type="password"/></div></div>
<button class="btn primary" onclick="saveUser()">Salvar</button><div id="usrList"></div>`);const d=await api('/api/company/users/list',{});usrList.innerHTML=table(['Nome','Email','Perfil','Status'],(d.items||[]).map(u=>[u.nome,u.email,u.perfil,u.status]))}
function saveUser(){api('/api/company/users/save',{nome:usrNome.value,email:usrEmail.value,perfil:usrPerfil.value,senha:usrSenha.value}).then(()=>loadUsers())}
async function loadFinance(){const d=await api('/api/company/finance',{});card('Financeiro corporativo',`<p><b>Total:</b> ${d.total_fmt||'R$ 0,00'}</p>
<button class="btn" onclick="exportFile('excel')">Exportar Excel</button> <button class="btn" onclick="exportFile('pdf')">Exportar PDF</button>
<div id="finTable"></div>`);finTable.innerHTML=table(['Numero','Data','Descricao','Centro','Status','Valor'],(d.items||[]).map(r=>[r.numero,r.data,r.descricao,r.centro_custo,r.status,r.valor]))}
function exportFile(kind){api('/api/company/export',{format:kind}).then(d=>{if(!d.ok)return alert('Falha exportacao');const blob=new Blob([kind==='excel'?atob(d.content):d.content],{type:d.mime||'text/plain'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=d.filename;a.click()})}
async function loadCalculator(){card('Calculadora',`<label>Origem</label><input id="calcOrigem"/><label>Destino</label><input id="calcDestino"/><label>Categoria</label><select id="calcCategoria"><option>Sedan</option><option>SUV</option><option>Van</option><option>Executivo</option></select>
<label>Distancia km</label><input id="calcKm" type="number"/><button class="btn primary" onclick="calcQuote()">Simular</button><div id="calcResult"></div>`)}
function calcQuote(){api('/api/company/quote',{origem:calcOrigem.value,destino:calcDestino.value,categoria:calcCategoria.value,km:calcKm.value}).then(d=>{calcResult.innerHTML=d.ok?('<p><b>Faixa:</b> '+d.quote.menor_valor+' a '+d.quote.maior_valor+'</p>'):('<p class="error">Sem parametros</p>')})}
async function loadCatalog(){const [v,h,a,l,cov]=await Promise.all([api('/api/company/gateway/vehicles',{}),api('/api/company/gateway/hotels',{}),api('/api/company/gateway/airports',{}),api('/api/company/gateway/locations',{}),api('/api/company/gateway/coverage',{})]);
card('Catalogo via Gateway V1',`<h3>Veiculos (${v.source||'local'})</h3>${table(['Categoria','Modelo','Capacidade'],(v.items||[]).map(x=>[x.categoria,(x.marca||'')+' '+(x.modelo||''),x.capacidade]))}
<h3>Hoteis</h3>${table(['Nome','Cidade','UF'],(h.items||[]).map(x=>[x.nome,x.cidade||x.cidade_nome,x.estado||x.estado_uf]))}
<h3>Aeroportos</h3>${table(['Nome','Cidade','UF'],(a.items||[]).map(x=>[x.nome,x.cidade||x.cidade_nome,x.estado||x.estado_uf]))}
<h3>Locations</h3>${table(['Nome','Tipo','Cidade'],(l.items||[]).slice(0,20).map(x=>[x.nome,x.tipo,x.cidade||x.cidade_nome]))}
<h3>Coverage</h3><p class="muted">Estados: ${cov.totals?.states??0} · Cidades: ${cov.totals?.cities??0}</p>`)}
if(token)boot();
</script></body></html>"""
