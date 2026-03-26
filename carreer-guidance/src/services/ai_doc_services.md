# Service Layer Spec

## 1. Scope
Folder: src/services/
Service la noi chua implementation thuc te va external I/O.

## 2. Sync-doc related services
- gemini/ocr_service: OCR extraction.
- document_service: prepare file + chunking.
- database_service: create/update/get status job qua repository.
- vector_db_services: upsert embeddings/chunks.

## 3. Rules
- Service business logic chay sync.
- Session DB chi su dung bang context manager trong service/database boundary.
- Nhan execution_id de logging/trace.
- Khong phat sinh business session_id cho sync flow.

## 4. Status management
- create job voi start.
- update processing trong luc chay.
- ket thuc failed hoac completed.

## 5. Reliability
- Co timeout/retry cho external call (neu co).
- Exception map ve service-level error de handler/module map tiep.
