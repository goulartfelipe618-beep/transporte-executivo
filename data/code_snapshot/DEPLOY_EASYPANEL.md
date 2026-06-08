# Deploy EasyPanel — sistema.transporteexecutivo.com

## Problema: redireciona para /vnc.html?autoconnect=1...

Isso e a **imagem Docker ANTIGA** (modo noVNC). Nosso codigo atual **nao faz** esse redirect.

A URL `?autoconnect=1&resize=scale&reconnect=1` foi gravada no `index.html` do noVNC na imagem velha.

## Correcao (EasyPanel)

1. **Environment** → **APAGUE** `NEXUS_SISTEMA_UI=vnc` (se existir)
2. Mantenha: `NEXUS_DEPLOY_TARGET=sistema`
3. **Dominios** → `sistema.transporteexecutivo.com` → porta **8772** (sem redirect customizado)
4. **Implantar** rebuild · branch `main` · `Dockerfile.sistema`

## Como saber se a imagem NOVA subiu

```bash
curl -s https://sistema.transporteexecutivo.com/api/deploy-info
```

**Imagem nova:**
```json
{"ok":true,"service":"sistema_web","mode":"web","build":"2026.08.17","stamp":"web-only","vnc_removed":true}
```

**Imagem antiga (VNC):** `/api/deploy-info` da 404 ou `/` redireciona para `/vnc.html`

```bash
curl -I https://sistema.transporteexecutivo.com/
```

**Nova:** `HTTP/2 200` e header `X-Nexus-Deploy: web-2026.08.17` (sem `Location: vnc.html`)

**Antiga:** `Location: /vnc.html?autoconnect=1...`

## Dentro do container (VPS)

```bash
docker ps --format "{{.Names}}" | grep sistema

docker exec NOME_CONTAINER cat /app/.nexus_sistema_ui
# deve: web-only

docker exec NOME_CONTAINER test -d /usr/share/novnc && echo IMAGEM_VNC_ANTIGA || echo imagem_web_ok
```

## URL correta

```
https://sistema.transporteexecutivo.com/
```

Login NT → painel com sidebar. Sem noVNC.

## VPS — verificar e matar VNC

```bash
cd /caminho/do/repo   # ou clone
bash scripts/vps_verificar_sistema.sh
```

Ou manual:

```bash
CONTAINER=$(docker ps --format '{{.Names}}' | grep sistema_do_projeto | head -1)
docker exec $CONTAINER cat /app/.nexus_sistema_ui          # web-only
docker exec $CONTAINER test -d /usr/share/novnc && echo VNC_ANTIGO
docker exec $CONTAINER python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8772/api/deploy-info').read())"
```

## Cloudflare

Se `curl -I` da 200 mas o browser abre noVNC: **Purge cache** do dominio `sistema.transporteexecutivo.com`.

## Forcar novo container (Swarm)

```bash
docker service ls | grep sistema
docker service update --force NOME_DO_SERVICO
```
