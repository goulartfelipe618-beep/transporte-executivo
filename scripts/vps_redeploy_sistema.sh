#!/bin/sh
# Redeploy Sistema Master Web na VPS (EasyPanel / Docker).
# Uso: ssh root@SUA_VPS 'bash -s' < scripts/vps_redeploy_sistema.sh
set -e

echo "=== Nexus — redeploy Sistema Master Web ==="

CONTAINER=$(docker ps --format '{{.Names}}' | grep -iE 'sistema|transporte|nexus' | head -1)
if [ -z "$CONTAINER" ]; then
  echo "ERRO: container nao encontrado. Containers ativos:"
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
  exit 1
fi

echo "Container: $CONTAINER"
echo ""
echo "--- Build ATUAL (antes) ---"
docker exec "$CONTAINER" python -c "
from pathlib import Path
for line in Path('/app/app/version.py').read_text(encoding='utf-8').splitlines():
    if line.startswith('APP_BUILD'):
        print(line.strip())
try:
    print('git:', Path('/app/.nexus_git_commit').read_text(encoding='utf-8').strip())
except OSError:
    print('git: (nao registrado)')
legacy = Path('/app/app/master/templates/master/reservations/form_edit.html')
unified = Path('/app/app/master/templates/master/reservations/form.html')
print('form_edit legado:', legacy.is_file())
print('form unificado:', unified.is_file())
"

echo ""
echo "Se build != 2026.06.26-reservas-edit2, faca REBUILD no EasyPanel:"
echo "  1. App Sistema -> Source: branch main"
echo "  2. Dockerfile: Dockerfile.sistema (NAO Dockerfile padrao)"
echo "  3. Botao Implantar / Rebuild (nao apenas Restart)"
echo "  4. Cloudflare: Purge cache sistema.transporteexecutivo.com"
echo ""
echo "Apos rebuild, valide:"
echo "  curl -s https://sistema.transporteexecutivo.com/api/deploy-info"
echo "  reservation_form_unified deve ser true"
