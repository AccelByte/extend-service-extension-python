# Example: Debugging a 500 Internal Server Error

This annotated example shows a realistic debugging session for this Python Extend Service Extension
app where `GetGuildProgress` returns `500 Internal Server Error`.

---

## The Report

A developer sends this message:

> *"My service is running but when I call GET `/v1/admin/namespace/mygame/progress/guild_001`
> I get 500. The service started fine."*

---

## Step 1 — Collect logs

Enable request logging and re-run:

```bash
PLUGIN_GRPC_SERVER_LOGGING_ENABLED=true PYTHONPATH=src venv/bin/python -m app
```

The developer shares the output:

```
INFO:grpc_interceptor.server_interceptor:GetGuildProgress
ERROR:app.services.my_service:Error in GetGuildProgress: [GET /cloudsave/v1/admin/namespaces/{namespace}/records/{key}][404] adminGetGameRecordHandlerV1NotFound
```

**What this tells us:**
- The request successfully passed auth (the logging interceptor logged the method name).
- The gRPC call reached `GetGuildProgress` in `src/app/services/my_service.py`.
- CloudSave returned a `404 Not Found` for the key `guildProgress_guild_001`.
- All SDK errors are blindly mapped to `StatusCode.INTERNAL`, propagating as HTTP 500.

---

## Step 2 — Read the service implementation

Looking at `src/app/services/my_service.py`:

```python
async def GetGuildProgress(
    self, request: GetGuildProgressRequest, context: Any
) -> GetGuildProgressResponse:
    # ...
    gp_key = self.format_guild_progress_key(request.guild_id.strip())

    response, error = await cs_service.admin_get_game_record_handler_v1_async(
        key=gp_key,
        namespace=request.namespace,
        sdk=self.sdk,
    )
    if error:
        await context.abort(StatusCode.INTERNAL, str(error))
        return  # Never reached, but needed for type checking
    # ...
```

**Problem identified:** Any CloudSave error — including a legitimate "record not found" —
is returned as `StatusCode.INTERNAL`. This is incorrect: a missing record should be
`StatusCode.NOT_FOUND`, which gRPC-Gateway maps to HTTP 404.

---

## Step 3 — Identify the error type

The AccelByte Python SDK raises typed exceptions. Add a temporary debug line:

```python
if error:
    print(type(error).__name__, str(error))
    await context.abort(StatusCode.INTERNAL, str(error))
```

Output:
```
AdminGetGameRecordHandlerV1NotFound [GET /cloudsave/...][404] adminGetGameRecordHandlerV1NotFound
```

The error class name `AdminGetGameRecordHandlerV1NotFound` is a specific exception from the
AccelByte Python SDK's generated CloudSave client.

---

## Step 4 — The fix

The correct behaviour is to distinguish "not found" from an actual internal error.
In `src/app/services/my_service.py`:

```python
# Before
if error:
    await context.abort(StatusCode.INTERNAL, str(error))
    return

# After — check the error class name since the SDK uses generated exception types
if error:
    if "NotFound" in type(error).__name__ or "404" in str(error):
        await context.abort(StatusCode.NOT_FOUND, f"Guild progress not found: {error}")
    else:
        await context.abort(StatusCode.INTERNAL, str(error))
    return
```

---

## Step 5 — Verify

```bash
# Should now return 404, not 500
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/v1/admin/namespace/mygame/progress/nonexistent_guild
# Expected: 404
```

With `grpcurl` (requires `ENABLE_REFLECTION=true`):
```bash
grpcurl -plaintext \
  -d '{"namespace":"mygame","guild_id":"nonexistent"}' \
  localhost:6565 service.Service/GetGuildProgress
# Expected: status NOT_FOUND
```

---

## Key takeaways from this session

1. **Read the log first** — the gRPC middleware already logs the error code and message.
   You often don't need a breakpoint to identify the layer where the failure occurred.
2. **Follow the error upward** — the HTTP 500 came from `codes.Internal` which came from
   a CloudSave 404. Each layer added wrapping; trace it back.
3. **Distinguish error types** — returning `codes.Internal` for every storage error hides
   useful information from callers. Map known error conditions to appropriate gRPC codes.
