# EchoLearn File Storage Design

Current storage backend is `LocalStorage`.

- File bytes are saved under `LOCAL_STORAGE_DIR`.
- Database stores metadata only: filename, storage key, content type, size, owner.
- File extension and size are validated before write.
- Storage is behind `StorageBackend`, so object storage can replace local storage later.
- User files are never stored directly in database rows.

