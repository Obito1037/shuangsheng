# EchoLearn RAG Design

RAG flow:

1. Input text or parse uploaded file.
2. Clean and split text with `ChunkService`.
3. Store `Document` and `DocumentChunk`.
4. Generate vectors through `ProviderRegistry.get_embedding_provider()`.
5. Store vectors as chunk metadata for the local vector store.
6. On question, call `QueryRewriteProvider`.
7. If Query Rewrite returns `provider_unavailable` such as vivo `code=-3002`, use the original query.
8. Embed query.
9. Retrieve chunks by cosine similarity from `MemoryVectorStore`.
10. Rerank through `SimilarityProvider`.
11. Build prompt with references.
12. Answer through `LlmProvider`.
13. Store `RagRun` and `RagReference`.
14. Return `answer + references`.

The vector store is intentionally behind a small service abstraction so it can later be replaced by a dedicated vector database.

