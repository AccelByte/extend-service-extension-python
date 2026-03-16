---
name: debugging-guide
description: Debug issues in this Python Extend app. Covers gRPC errors, auth failures, CloudSave SDK errors, environment misconfiguration, and local vs Docker runtime problems.
user-invocable: true
allowed-tools: Bash, Read, Glob, Grep
argument-hint: [error message or symptom description]
---

# Debugging Guide

Diagnose and fix issues in this Python Extend Service Extension app.

## Arguments

`$ARGUMENTS`

Parse for:
- **Error message or symptom**: What the user sees (stack trace, gRPC status code, HTTP error, silent failure, etc.)
- If empty, run the full checklist below

## Architecture Reminder

```
Game Client → AGS Gateway → [REST :8000] → gRPC-Gateway (Go) → [gRPC :6565] → Python App
```

Issues can originate at any layer. Start by identifying the layer first.

---

## Step 1: Identify the layer

Ask (or infer from the error):

| Symptom | Likely layer |
|---|---|
| HTTP 4xx/5xx from REST endpoint | gRPC-Gateway or Python app |
| `UNAUTHENTICATED` or `PERMISSION_DENIED` gRPC status | Auth interceptor |
| `INVALID_ARGUMENT` or `INTERNAL` gRPC status | Service implementation |
| `Connection refused` on port 6565 | Python app not running |
| `Connection refused` on port 8000 | Gateway not running |
| Token/login error at startup | `AB_*` env vars or SDK login |
| CloudSave read/write failure | AccelByte SDK or wrong namespace |

---

## Step 2: Check environment

### 2a. Verify `.env` exists and is populated

```bash
cat .env
```

Required variables — flag any that are empty or missing:

| Variable | Description |
|---|---|
| `AB_BASE_URL` | AccelByte base URL (e.g. `https://test.accelbyte.io`) |
| `AB_NAMESPACE` | Target namespace |
| `AB_CLIENT_ID` | OAuth client ID |
| `AB_CLIENT_SECRET` | OAuth client secret |
| `PLUGIN_GRPC_SERVER_AUTH_ENABLED` | `true` to require bearer tokens |

If `.env` is missing:
```bash
cp .env.template .env
# then fill in credentials
```

### 2b. Check optional feature flags

| Variable | Effect when `true` |
|---|---|
| `ENABLE_HEALTH_CHECK` | Registers gRPC health check endpoint |
| `ENABLE_PROMETHEUS` | Starts Prometheus metrics on port 8080 |
| `ENABLE_REFLECTION` | Enables gRPC reflection (useful for grpcurl) |
| `ENABLE_ZIPKIN` | Enables Zipkin distributed tracing |
| `PLUGIN_GRPC_SERVER_LOGGING_ENABLED` | Logs each gRPC call at DEBUG level |
| `PLUGIN_GRPC_SERVER_METRICS_ENABLED` | Increments Prometheus counter per call |

---

## Step 3: Check startup errors

The app entry point is `src/app/__main__.py`. It **fails fast** if:

1. `AB_BASE_URL`, `AB_CLIENT_ID`, `AB_CLIENT_SECRET`, or `AB_NAMESPACE` are missing → `ValueError` from `src/app/utils.py`
2. `login_client_async()` fails → SDK raises an exception if credentials are wrong or `AB_BASE_URL` is unreachable

To run the app directly:
```bash
PYTHONPATH=src venv/bin/python -m app
```

Look for:
- `ValueError: missing required env vars` — fix `.env`
- `AccelByteException` or HTTP errors from the SDK — wrong credentials or unreachable base URL
- `Address already in use` on port 6565 — another process is using the port

---

## Step 4: Debug gRPC errors

### `UNAUTHENTICATED`

The auth interceptor (`src/accelbyte_grpc_plugin/interceptors/authorization.py`) rejected the call.

Check:
1. Is `PLUGIN_GRPC_SERVER_AUTH_ENABLED=true`? If so, every protected method requires `Authorization: Bearer <token>` metadata.
2. Is the token expired or revoked? `CachingTokenValidator` checks with AGS.
3. Does the token's `extend_namespace` claim match `AB_NAMESPACE`? Mismatch → `PERMISSION_DENIED`.

Enable logging to see the interceptor decisions:
```bash
PLUGIN_GRPC_SERVER_LOGGING_ENABLED=true PYTHONPATH=src venv/bin/python -m app
```

### `PERMISSION_DENIED`

Three causes in the auth interceptor:
1. `InsufficientPermissionsError` — token lacks the required resource/action (check `proto/service.proto` permission annotations)
2. `TokenRevokedError` / `UserRevokedError` — token has been revoked in AGS
3. `extend_namespace` mismatch — token was issued for a different namespace

### `INVALID_ARGUMENT`

The service implementation (`src/app/services/my_service.py`) explicitly aborts with this status when required fields are missing (e.g. empty `namespace` field in the request). Check what fields the endpoint requires from `proto/service.proto`.

### `INTERNAL`

Usually an unhandled SDK error. Check:
1. CloudSave API call in `my_service.py` — did `admin_post_game_record_handler_v1_async` or `admin_get_game_record_handler_v1_async` return an error?
2. The response object error field: the SDK returns `(result, error)` tuples — check `error is not None`.
3. Network connectivity to `AB_BASE_URL` from the running container/process.

---

## Step 5: Debug CloudSave / SDK issues

The service stores guild progress records with keys like `guildProgress_{guild_id}` in CloudSave.

Common issues:

| Symptom | Cause | Fix |
|---|---|---|
| `INTERNAL` on write | SDK error from CloudSave | Check `AB_NAMESPACE` matches the namespace in the request |
| Record not found on read | Wrong key or wrong namespace | Verify `guild_id` and namespace are consistent between write and read |
| SDK login fails at startup | Wrong `AB_CLIENT_ID`/`AB_CLIENT_SECRET` | Verify credentials in AGS Admin Portal |
| `accelbyte_py_sdk` import error | Missing dependencies | Run `venv/bin/pip install -r requirements.txt` |

To inspect SDK calls, enable OpenTelemetry tracing (`ENABLE_ZIPKIN=true`) or add temporary print statements in `my_service.py`.

---

## Step 6: Check Docker / Docker Compose issues

### Service won't start in Docker

```bash
docker compose up --build
docker compose logs app
```

Look for the same startup errors as Step 3. In Docker, `AB_*` env vars must be set in `.env` (Docker Compose reads it automatically).

Port mapping:
- `6565` → gRPC server
- `8000` → gRPC-Gateway (REST)
- `8080` → Prometheus metrics (if enabled)

### Gateway can't connect to app

The gateway connects to `host.docker.internal:6565` (Docker) or `localhost:6565` (devcontainer). If the Python app is not listening on 6565, the gateway will fail with a connection error. Verify the app started cleanly (Step 3).

---

## Step 7: Debug with grpcurl

If `ENABLE_REFLECTION=true`, use `grpcurl` to call gRPC endpoints directly (bypasses the HTTP gateway):

```bash
# List available services
grpcurl -plaintext localhost:6565 list

# Call an endpoint (no auth)
grpcurl -plaintext -d '{"namespace":"mynamespace","guild_id":"guild1"}' \
  localhost:6565 service.Service/GetGuildProgress

# Call with auth token
grpcurl -plaintext \
  -H "Authorization: Bearer <token>" \
  -d '{"namespace":"mynamespace","guild_id":"guild1"}' \
  localhost:6565 service.Service/GetGuildProgress
```

---

## Step 8: Regenerate proto files

If you see import errors for `service_pb2`, `service_pb2_grpc`, or `permission_pb2`, the generated files may be stale after a proto change.

```bash
make proto
```

This rebuilds the Docker image for the proto generator and regenerates:
- `src/service_pb2.py`, `src/service_pb2_grpc.py`, `src/service_pb2.pyi`
- `src/permission_pb2.py`, `src/permission_pb2_grpc.py`, `src/permission_pb2.pyi`
- Go gateway files in `gateway/pkg/pb/`

---

## Step 9: Lint and type errors

Run pylint to catch code issues:
```bash
venv/bin/pylint src/
```

Config is in `.pylintrc`. Fix any `E` (error) level issues first.

---

## Summary checklist

- [ ] `.env` exists and all `AB_*` variables are set
- [ ] Python app starts without errors (`PYTHONPATH=src venv/bin/python -m app`)
- [ ] Port 6565 is listening (`ss -tlnp | grep 6565`)
- [ ] Gateway running on port 8000
- [ ] If auth errors: check `PLUGIN_GRPC_SERVER_AUTH_ENABLED` and token claims
- [ ] If SDK errors: check credentials, namespace, and CloudSave record keys
- [ ] If proto import errors: run `make proto`
- [ ] If Docker issues: check `docker compose logs app`

---

## Additional resources

- For an annotated end-to-end debugging session, see [examples/debug-session.md](examples/debug-session.md)
