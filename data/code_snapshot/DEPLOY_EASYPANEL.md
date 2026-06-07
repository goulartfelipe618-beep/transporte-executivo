# Deploy no EasyPanel — Sistema vs Motor

Dois apps **separados** no mesmo repositório GitHub.

---

## Método A — App (funciona mesmo se EasyPanel ignorar Dockerfile.sistema)

| Campo | Valor |
|-------|-------|
| Tipo | **App** |
| Fonte | GitHub `transporte-executivo` / `main` |
| Construção | **Dockerfile** (`Dockerfile` ou `Dockerfile.sistema`) |
| Domínio → Porta | **8770** |

### Variável OBRIGATÓRIA (aba Ambiente / Environment)

```env
NEXUS_DEPLOY_TARGET=sistema
```

Sem isso o container sobe o **Motor** (`uvicorn`) e dá erro de `SECRET_KEY`.

Demais variáveis: ver `.env.sistema.example`.

**Implantar** → botão verde **Implantar** (Rebuild). Restart não basta.

> Nem toda versão do EasyPanel mostra campos "Comando" / "Argumentos". Se não existir, ignore — use o Método B.

---

## Método B — Compose (recomendado se continuar uvicorn)

Mais confiável: o compose **força** `Dockerfile.sistema` no build.

1. **+ Serviço** → escolha **Compose** (não App)
2. Repositório: `goulartfelipe618-beep/transporte-executivo` / `main`
3. Arquivo compose: **`docker-compose.sistema.yml`**
4. Serviço alvo do domínio: **`sistema`**
5. Domínio `api.transporteexecutivo.com` → porta **8770**
6. Variáveis de ambiente (aba Env):

```env
APP_ENV=production
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
NEXUS_BIND_HOST=0.0.0.0
INTEGRACAO_GATEWAY_HOST=0.0.0.0
GATEWAY_MOCK_FALLBACK=false
```

7. **Salvar** → **Implantar**

---

## App Motor (`engine.transporteexecutivo.com`)

| Campo | Valor |
|-------|-------|
| Tipo | App |
| Dockerfile | **`Dockerfile`** |
| Porta domínio | **8000** |
| Env | `.env.motor.example` |

---

## Como saber se a build certa subiu

### Log de RUNTIME — certo (Sistema)

```text
[Nexus] === SISTEMA MASTER (headless) — porta 8770 ===
[Nexus] Servicos ativos.
```

### Log de RUNTIME — errado (ainda Motor)

```text
/usr/local/bin/uvicorn
secret_key Field required
```

### Teste HTTP

```text
https://api.transporteexecutivo.com/api/v1/public/statistics
```

JSON = Sistema ok. Landing "Iniciar reserva" = Motor no domínio errado.

### Console do container (opcional)

Dentro do app, aba **Console** → Launcher:

```bash
cat /app/.nexus_build_target
```

Deve imprimir: `sistema-master-8770`. Se o arquivo não existir, a imagem errada foi buildada.

---

## Subir a build (passo a passo)

1. `git push` no PC (código no GitHub)
2. EasyPanel → abrir o serviço
3. Conferir Dockerfile **ou** compose (acima)
4. Clicar **Implantar** (não só Reiniciar)
5. Abrir **Logs** e esperar `SISTEMA MASTER`
