# Deploy EasyPanel — 5 dominios

## Servico 1: Sistema Master (`sistema_do_projeto`)

Compose: `docker-compose.sistema.yml` · Portas: **8770, 8772, 8765, 8766**

| Dominio | Porta | O que abre |
|---------|-------|------------|
| `api.transporteexecutivo.com` | 8770 | API gateway |
| `sistema.transporteexecutivo.com` | 8772 | **Painel Tkinter real** (noVNC) |
| `driver.transporteexecutivo.com` | 8765 | Portal motorista |
| `business.transporteexecutivo.com` | 8766 | Portal empresa |

Env obrigatorio:

```
NEXUS_DEPLOY_TARGET=sistema
NEXUS_SISTEMA_UI=vnc
```

## Painel sistema.transporteexecutivo.com

Com `NEXUS_SISTEMA_UI=vnc` (padrao), abre o **mesmo sistema desktop** no navegador:

1. Acesse: `https://sistema.transporteexecutivo.com/vnc.html?autoconnect=1&resize=scale&reconnect=1`
2. Aparece a tela de login **Central Operacional Master** (NT, Supabase)
3. Apos login: **TRANSPORTE EXEC.** com sidebar, Abrangencia, Empresas, etc.

Nao e copia HTML — e o Tkinter rodando no servidor via display virtual.

Para voltar ao painel HTML simplificado: `NEXUS_SISTEMA_UI=web`

## Servico 2: Motor (`transporteexecutivo_com`)

Dockerfile padrao · Porta **8000** · Dominio `engine.transporteexecutivo.com`

## Deploy

1. EasyPanel → **Implantar** (rebuild) · branch `main` · `Dockerfile.sistema`
2. Comando/Argumentos: **vazio**
3. WebSocket habilitado no dominio `sistema.*` (Traefik/EasyPanel costuma fazer automatico)

## Log esperado

```
[Nexus] Painel Tkinter real via noVNC (porta 8772)
[Nexus] GUI Tkinter disponivel em noVNC porta 8772
[Nexus] Iniciando main.py (TransferSystemApp)...
```

## Validar

```bash
curl -I https://sistema.transporteexecutivo.com/vnc.html
curl https://api.transporteexecutivo.com/api/v1/public/statistics
```
