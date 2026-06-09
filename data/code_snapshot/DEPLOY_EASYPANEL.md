# Deploy EasyPanel — Plataforma Transporte Executivo (P3.1)

## Topologia (2 apps EasyPanel)

| Domínio | Serviço | Porta container | Dockerfile |
|---------|---------|-----------------|------------|
| `api.transporteexecutivo.com` | API Gateway v1 | **8770** | `Dockerfile.sistema` |
| `sistema.transporteexecutivo.com` | Master Web FastAPI | **8772** | `Dockerfile.sistema` |
| `driver.transporteexecutivo.com` | Portal Motorista | **8765** | `Dockerfile.sistema` |
| `business.transporteexecutivo.com` | Portal Empresa | **8766** | `Dockerfile.sistema` |
| `engine.transporteexecutivo.com` | Motor de Reservas | **8000** | `Dockerfile` |

**App 1 — Sistema:** um container, quatro domínios, quatro portas HTTP.  
**App 2 — Motor:** container separado, porta 8000.

---

## App Sistema — variáveis obrigatórias

```env
NEXUS_DEPLOY_TARGET=sistema
NEXUS_SISTEMA_UI=web
APP_ENV=production

SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

NEXUS_BIND_HOST=0.0.0.0
INTEGRACAO_GATEWAY_HOST=0.0.0.0
GATEWAY_MOCK_FALLBACK=false

MASTER_SECRET_KEY=...minimo-32-caracteres...

SISTEMA_WEB_BASE_URL=https://sistema.transporteexecutivo.com
DRIVER_PORTAL_BASE_URL=https://driver.transporteexecutivo.com
COMPANY_PORTAL_BASE_URL=https://business.transporteexecutivo.com
INTEGRACAO_API_BASE_URL=https://api.transporteexecutivo.com
ENGINE_BASE_URL=https://engine.transporteexecutivo.com
```

**Proibido:** `NEXUS_SISTEMA_UI=vnc` (imagem legada noVNC).

Copiar base: `.env.sistema.example`

---

## App Motor — variáveis obrigatórias

```env
APP_ENV=production
SECRET_KEY=...minimo-32...
JWT_SECRET_KEY=...minimo-32...
CSRF_SECRET_KEY=...minimo-32...

DATABASE_URL=postgresql+asyncpg://...
ALLOWED_HOSTS=engine.transporteexecutivo.com
HEALTHCHECK_HOST=engine.transporteexecutivo.com
BASE_URL=https://engine.transporteexecutivo.com

GATEWAY_API_BASE_URL=https://api.transporteexecutivo.com
GATEWAY_MOCK_FALLBACK=false

SUPABASE_URL=...
SUPABASE_ANON_KEY=...

CORS_ORIGINS=https://engine.transporteexecutivo.com
```

Copiar base: `.env.motor.example`

---

## Implantar Sistema (EasyPanel)

1. Repositório branch `main`, commit ≥ `055a36e`, build ≥ `2026.09.09`
2. **Dockerfile:** `Dockerfile.sistema` (não usar `Dockerfile` padrão)
3. **Build args (opcional):** `NEXUS_GIT_COMMIT=<sha>`
4. Mapear domínios → portas conforme tabela acima
5. **Implantar / Rebuild** (force new container)
6. Cloudflare: **Purge cache** nos 5 domínios

---

## Validar deploy

```bash
# Build e health Sistema
curl -s https://sistema.transporteexecutivo.com/api/deploy-info
# build >= 2026.09.09, mode: web, vnc_removed: true

curl -s https://api.transporteexecutivo.com/api/v1/public/statistics
curl -s https://engine.transporteexecutivo.com/health

# Portal Empresa — URL canônica (requer portal_codigo no Supabase)
curl -I https://business.transporteexecutivo.com/emp-000001/DXSKJJBJEWRQ
# HTTP 200

# Script completo (repo)
python scripts/p31_production_validate.py
```

Na VPS:

```bash
bash scripts/vps_verificar_sistema.sh
```

---

## Causa do 404 em `/emp-000001/{codigo}` (P3)

1. **Imagem desatualizada** — VPS em build `2026.08.19` anterior às correções P2.4/P2.5
2. **`portal_codigo` ausente** no Supabase antes do saneamento P2.4 — `find_company_by_path()` retorna None → 404
3. **Container não reiniciado** após persistência do `portal_codigo` no Supabase

O código atual (≥ `2026.09.09`) serve a rota canônica corretamente quando `portal_codigo` está em `dados_extra`.

---

## Problema legado: redireciona para `/vnc.html`

Imagem Docker **antiga** (modo noVNC). Correção:

1. Apagar `NEXUS_SISTEMA_UI=vnc`
2. Rebuild com `Dockerfile.sistema`
3. Confirmar `/app/.nexus_sistema_ui` = `web-only`
4. Confirmar ausência de `/usr/share/novnc`

---

## Rollback

1. EasyPanel → redeploy imagem anterior (tag/commit guardado)
2. `docker service update --force <servico>`
3. Supabase point-in-time restore se necessário
4. Purge cache Cloudflare

---

## Compose local (referência)

```bash
docker compose -f docker-compose.sistema.yml up --build
docker compose -f docker-compose.yml up --build   # motor
```
