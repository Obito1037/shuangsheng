# EchoLearn Database Design

SQLAlchemy models:

- `User`
- `RefreshToken`
- `Device`
- `Conversation`
- `Message`
- `LearningRecord`
- `FileObject`
- `Document`
- `DocumentChunk`
- `KnowledgeBase`
- `RagRun`
- `RagReference`
- `UsageRecord`

Repositories:

- `UserRepository`: user lookup and creation
- `TokenRepository`: refresh token creation, validation, revocation
- `ConversationRepository`: conversation ownership-scoped CRUD
- `MessageRepository`: message persistence and conversation history
- `LearningRepository`: learning record storage
- `FileRepository`: file metadata CRUD
- `DocumentRepository`: documents and chunks
- `KnowledgeRepository`: knowledge bases and RAG run/reference persistence
- `UsageRepository`: usage records and token totals

SQLite is the local default. The schema avoids SQLite-only types so it can move to PostgreSQL through Alembic migrations.

