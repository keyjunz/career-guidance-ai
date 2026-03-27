# Repository Layer Spec

## 1. Scope
Folder: src/repositories/
Repository gom query/persistence methods, khong chua business orchestration.

## 2. Rule chung
- Tat ca method la sync.
- Session duoc truyen vao tu service layer.
- Commit/rollback quan ly o session_scope, khong commit roi rac trong tung method.

## 3. DocumentRepository
- Bulk upsert metadata cho sync-doc.
- Query theo ingestion_job_id de phuc vu polling status.

## 4. Boundary
- Khong map HTTP response o repository.
- Khong call external API o repository.
