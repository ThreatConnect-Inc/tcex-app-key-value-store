# tcex-app-key-value-store

A [TcEx](https://github.com/ThreatConnect-Inc/tcex) submodule providing the key-value store
abstraction layer used by Playbook and Service Apps to read and write variables during execution.

## Overview

ThreatConnect Playbook and Service Apps exchange data through a key-value store backed by Redis
(in-platform) or the TC KeyValue API (legacy/API-mode). This submodule provides a unified interface
over all supported backends, a factory class that selects the correct backend at runtime, and an
in-memory mock for local testing. It also includes connection pool wrappers for plain and TLS Redis
connections.

## Architecture

All backend classes implement the `KeyValueABC` abstract interface (`create` / `read`). The
`KeyValueStore` factory selects the appropriate implementation based on the `tc_kvstore_type`
runtime parameter injected by the ThreatConnect platform.

```
KeyValueStore (factory)
├── KeyValueRedis   ← tc_kvstore_type = 'Redis'
├── KeyValueApi     ← tc_kvstore_type = 'TCKeyValueAPI'
└── KeyValueMock    ← tc_kvstore_type = 'Mock'  (testing only)
```

The **context** argument present on every read/write call is the Playbook execution ID (or service
context). It maps to a Redis hash key, so all variables for a single execution are stored together
and naturally isolated from other executions.

## Module Reference

### `KeyValueABC`

Abstract base class that defines the two-method contract shared by all backends:

- `create(context, key, value)` — write a value under a key within the given context.
- `read(context, key)` — retrieve a value by key from the given context.

### `KeyValueRedis`

Redis-backed implementation. Wraps a `redis.Redis` client and maps operations to Redis hash
commands (`HSET` / `HGET` / `HDEL` / `HGETALL`), using the context as the hash name. Additional
methods beyond the base interface:

- `delete(context, key)` — remove a single key from the context hash.
- `hget(context, key)` — raw `HGET`; returns bytes without any decoding.
- `hgetall(context)` / `get_all(context)` — return the full hash for a context as a dict.

### `KeyValueApi`

ThreatConnect API-backed implementation. Communicates with the internal TC REST endpoint
`/internal/playbooks/keyValue/{context}/{key}` over an authenticated `requests.Session`.
Supports only `create` (HTTP `PUT`) and `read` (HTTP `GET`). Binary response content is decoded
from UTF-8 before being returned.

### `KeyValueMock`

Purely in-memory implementation backed by a class-level `dict` and a `threading.Lock`. Intended
**only** for local testing — the framework logs a warning if this backend is selected at runtime.
The class-level store means all `KeyValueMock` instances within a process share the same data,
matching the behavior of a shared Redis instance in tests. Supports `create`, `read`, and
`get_all`.

### `KeyValueStore`

Top-level factory and coordinator. Accepts all TC runtime KV store parameters and lazily
constructs the correct backend via the `client` cached property:

| `tc_kvstore_type` | Backend returned |
|---|---|
| `'Redis'` | `KeyValueRedis` (using `redis_client`) |
| `'TCKeyValueAPI'` | `KeyValueApi` (using `session_tc`) |
| `'Mock'` | `KeyValueMock` |
| anything else | raises `RuntimeError` |

Additional properties:

- `client_kvr` — always returns a `KeyValueRedis`, regardless of `tc_kvstore_type`. Used by
  Service Apps that need direct Redis access alongside the standard KV store.
- `redis_client` — a configured `redis.Redis` instance, plain or TLS depending on
  `tc_kvstore_tls_enabled`.
- `get_redis_client()` / `get_redis_client_ssl()` — static factories that return a fresh
  `redis.Redis` instance (not pooled) for one-off use.

### `RedisClient`

Manages a single shared `redis.ConnectionPool` for plain (non-TLS) connections. Registers
`atexit` handlers to disconnect the pool and close the client on process exit.

### `RedisClientSsl`

TLS variant of `RedisClient`. Uses `redis.SSLConnection` with `ssl_cert_reqs='required'` and
accepts optional CA cert, client cert, and client key paths for mutual TLS. Also registers
`atexit` cleanup handlers.

## Project Structure Note — No `pyproject.toml` or `.pre-commit-config.yaml`

This submodule intentionally ships **without** a `pyproject.toml` or `.pre-commit-config.yaml`.
All linting (`ruff`), type-checking (`ty`), and pre-commit hooks are configured in the **parent
projects** (`tcex`, `tcex-app-testing`), each of which scans this submodule as part of its own
workspace. Running `pre-commit run --all-files` or `ty check` from the parent repo root covers
this code automatically — there is no need for (and no benefit to) duplicating that configuration
here.

## Used By

- [tcex](https://github.com/ThreatConnect-Inc/tcex) — runtime KV store access for Playbook and Service Apps
- [tcex-app-testing](https://github.com/ThreatConnect-Inc/tcex-app-testing) — `KeyValueMock` and Redis fixtures for test harnesses

## License

Apache 2.0 — see [LICENSE](LICENSE).
