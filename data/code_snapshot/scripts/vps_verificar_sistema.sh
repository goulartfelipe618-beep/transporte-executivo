#!/bin/sh
# Rode na VPS como root: bash scripts/vps_verificar_sistema.sh
set -e

echo "=== Nexus — verificar VNC vs WEB ==="

CONTAINER=$(docker ps --format '{{.Names}}' | grep -i sistema_do_projeto | head -1)
if [ -z "$CONTAINER" ]; then
  echo "ERRO: container sistema_do_projeto nao encontrado."
  docker ps --format 'table {{.Names}}\t{{.Status}}'
  exit 1
fi
echo "Container: $CONTAINER"

echo ""
echo "--- Stamp deploy ---"
docker exec "$CONTAINER" cat /app/.nexus_sistema_ui 2>/dev/null || echo "ARQUIVO_AUSENTE (imagem antiga)"

echo ""
echo "--- noVNC na imagem? (deve falhar) ---"
if docker exec "$CONTAINER" test -d /usr/share/novnc 2>/dev/null; then
  echo "IMAGEM_VNC_ANTIGA: /usr/share/novnc existe — faca REBUILD no EasyPanel"
else
  echo "OK: sem /usr/share/novnc"
fi

echo ""
echo "--- Processos VNC (deve estar vazio) ---"
docker exec "$CONTAINER" sh -c "ps aux 2>/dev/null | grep -E 'websockify|x11vnc|Xvfb' | grep -v grep || echo OK: sem processos VNC"

echo ""
echo "--- Porta 8772 interna ---"
docker exec "$CONTAINER" python -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:8772/api/deploy-info', timeout=5)
    print('deploy-info:', r.read().decode())
except Exception as e:
    print('FALHOU deploy-info:', e)
try:
    r = urllib.request.urlopen('http://127.0.0.1:8772/', timeout=5)
    body = r.read(400).decode('utf-8', errors='replace')
    if 'vnc.html' in body or 'noVNC' in body or 'autoconnect' in body:
        print('ERRO: HTML da raiz ainda e VNC/noVNC')
    elif 'Central Operacional Master' in body:
        print('OK: login WEB na raiz')
    else:
        print('HTML raiz (inicio):', body[:200])
except Exception as e:
    print('FALHOU raiz:', e)
"

echo ""
echo "--- Env NEXUS_SISTEMA_UI no container ---"
docker exec "$CONTAINER" printenv NEXUS_SISTEMA_UI 2>/dev/null || echo "(nao definido = ok)"

echo ""
echo "--- Logs recentes ---"
docker logs "$CONTAINER" --tail 12 2>&1

echo ""
echo "=== Se aparecer IMAGEM_VNC_ANTIGA ==="
echo "1. EasyPanel: APAGUE variavel NEXUS_SISTEMA_UI=vnc"
echo "2. EasyPanel: Implantar rebuild (main + Dockerfile.sistema)"
echo "3. Cloudflare: Purge cache de sistema.transporteexecutivo.com"
echo "4. Abra: https://sistema.transporteexecutivo.com/ (sem /vnc.html)"
