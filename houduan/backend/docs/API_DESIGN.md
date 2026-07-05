# EchoLearn API Design

Implemented endpoints:

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET /api/users/me`
- `POST /api/chat/message`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `POST /api/files/upload`
- `GET /api/files`
- `GET /api/files/{file_id}`
- `DELETE /api/files/{file_id}`
- `POST /api/documents/parse`
- `POST /api/knowledge-bases`
- `GET /api/knowledge-bases`
- `POST /api/rag/index-text`
- `POST /api/rag/index-document`
- `POST /api/rag/ask`
- `GET /api/usage/me`

Protected endpoints require `Authorization: Bearer <access_token>`. Android should call EchoLearn backend APIs only; it must not call third-party AI APIs directly.

## Android client usage

1. Call `POST /api/auth/register` or `POST /api/auth/login` and persist the returned `access_token` and `refresh_token`.
2. Send protected requests with `Authorization: Bearer <access_token>`.
3. Refresh expired access tokens through `POST /api/auth/refresh`; revoke refresh tokens through `POST /api/auth/logout`.
4. Upload files with `multipart/form-data` field name `upload` to `POST /api/files/upload`, then parse with `POST /api/documents/parse`.
5. Use `POST /api/knowledge-bases`, `POST /api/rag/index-text` or `POST /api/rag/index-document`, and `POST /api/rag/ask` for RAG workflows.
6. Never ship provider AppId/AppKey in Android. Third-party calls stay behind EchoLearn backend Provider Registry for rate limiting, redaction, auditing, fallback, and replacement.
