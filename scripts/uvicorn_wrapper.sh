#!/bin/sh
# EasyPanel inicia /usr/local/bin/uvicorn direto — este wrapper redireciona o Sistema Master.
set -e

_sistema_mode() {
  case "${NEXUS_DEPLOY_TARGET:-}" in
    [Ss][Ii][Ss][Tt][Ee][Mm][Aa]|sistema) return 0 ;;
  esac
  case "${PRIMARY_DOMAIN:-}${EASYPANEL_DOMAIN:-}" in
    *api.transporteexecutivo.com*) return 0 ;;
  esac
  return 1
}

if _sistema_mode; then
  echo "[Nexus] uvicorn_wrapper -> Sistema Master (NEXUS_DEPLOY_TARGET=${NEXUS_DEPLOY_TARGET:-})"
  exec python /app/scripts/run_production_server.py
fi

exec /usr/local/bin/_uvicorn_motor "$@"
