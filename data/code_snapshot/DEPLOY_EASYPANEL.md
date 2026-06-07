# Deploy no EasyPanel — Sistema vs Motor

Dois apps **separados** no mesmo repositório GitHub.

## App 1 — Sistema Master (`api.transporteexecutivo.com`)

| Campo | Valor |
|-------|-------|
| Fonte | GitHub `transporte-executivo` / branch `main` |
| Construção | **Dockerfile** |
| Arquivo Dockerfile | **`Dockerfile.sistema`** |
| Domínio → Porta proxy | **8770** |
| Variáveis | Ver `.env.sistema.example` |

### CRÍTICO — Configurações de deploy

Em **Implantar** → **Configurações de deploy** (Deploy settings):

| Campo | Valor |
|-------|-------|
| **Comando** (Command) | **vazio** |
| **Argumentos** (Arguments) | **vazio** |

Se houver `uvicorn` ou `app.main:app` nesses campos, o EasyPanel **ignora** o `Dockerfile.sistema` e você verá:

```text
/usr/local/bin/uvicorn
ValidationError: secret_key / jwt_secret_key / csrf_secret_key
```

Após alterar: **Salvar** → **Implantar (Rebuild)**.

### Log correto (Sistema)

```text
[Nexus] === SISTEMA MASTER (headless) ===
[Nexus] Runtime producao build ...
[Nexus] Servicos ativos.
```

### Teste

```text
https://api.transporteexecutivo.com/api/v1/public/statistics
```

Deve retornar JSON (KPIs de cobertura).

---

## App 2 — Motor de Reservas (`engine.transporteexecutivo.com`)

| Campo | Valor |
|-------|-------|
| Arquivo Dockerfile | **`Dockerfile`** |
| Domínio → Porta proxy | **8000** |
| Variáveis | Ver `.env.motor.example` (inclui SECRET_KEY, JWT_*, CSRF_*, DATABASE_URL) |

Comando/Argumentos: vazio (usa `uvicorn` do Dockerfile) **ou** deixe o padrão do Motor.

### Teste

```text
https://engine.transporteexecutivo.com/health
```

---

## Build — como confirmar qual imagem subiu

No log de **build** do app Sistema, a imagem deve expor porta **8770**, não 8000.

No log de **runtime**, a primeira linha deve mencionar `SISTEMA MASTER`, nunca `uvicorn`.
