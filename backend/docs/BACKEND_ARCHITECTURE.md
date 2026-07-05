# EchoLearn Backend Architecture

EchoLearn backend is layered as:

```text
FastAPI API -> Service -> Repository -> SQLAlchemy models -> Database
                         -> Provider Registry -> Third-party Provider
                         -> Storage Backend
```

API modules only translate HTTP request/response payloads. Services orchestrate business flow. Repositories own database access. Provider calls go through `ProviderRegistry`, never directly through concrete `Vivo*Provider` classes.

Current local defaults:

- API framework: FastAPI
- Database: SQLite via SQLAlchemy, migratable to PostgreSQL
- Storage: local filesystem through `StorageBackend`
- Authentication: PBKDF2 password hash, HMAC-signed bearer access token, revocable refresh token hash
- RAG: DB-backed chunk metadata and local memory vector search

