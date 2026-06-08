# Deploy EasyPanel — 5 dominios

## Servico: Sistema Master (`sistema_do_projeto`)

| Dominio | Porta |
|---------|-------|
| `api.transporteexecutivo.com` | 8770 |
| `sistema.transporteexecutivo.com` | 8772 |
| `driver.transporteexecutivo.com` | 8765 |
| `business.transporteexecutivo.com` | 8766 |

## Env obrigatorio

```
NEXUS_DEPLOY_TARGET=sistema
NEXUS_SISTEMA_UI=web
```

**NAO use** `NEXUS_SISTEMA_UI=vnc` — modo legado removido do padrao.

## sistema.transporteexecutivo.com

Abre **direto no navegador**:

1. `https://sistema.transporteexecutivo.com/` — login (igual desktop: NT, Supabase)
2. Apos entrar — painel com sidebar (Abrangencia, Empresas, Reservas...)

**Nao use** `/vnc.html` — URL antiga redireciona para `/`.

## Deploy

1. Branch `main` · `Dockerfile.sistema` · **Implantar** (rebuild)
2. Comando/Argumentos: vazio

## Log esperado

```
[Nexus] Painel web direto porta 8772 — build 2026.08.15
[Nexus] URL: https://sistema.transporteexecutivo.com/ (sem vnc.html)
[Nexus] Sistema web: https://sistema.transporteexecutivo.com
```

## Validar

```bash
curl -s https://sistema.transporteexecutivo.com/api/health
# {"ok": true, "service": "sistema_web", "build": "2026.08.15", ...}
```
