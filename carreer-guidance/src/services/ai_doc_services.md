# Service Layer Spec

## 1. Scope
Folder: src/services/
Service chua implementation thuc te va external I/O.

## 2. Danh sach service hien tai
- database_service/main.py: create/update/query sync-doc job status.
- document_service/main.py: download file + split text chunks.
- gemini/main.py: OCR extraction qua Gemini generateContent API.
- vector_db_service/main.py: archive chunks ra JSONL (placeholder vector pipeline).
- redis_service/main.py: enqueue/dequeue payload tu Redis queue.
- dispatcher_service/main.py: dispatch chat async request vao queue.
- dispatcher_service/chat_worker_service.py: worker loop dequeue va process sync.

## 3. Rule chung
- Service nhan execution_id trong constructor.
- Khong dat logic route/response map o service.
- DB session chi dung context manager (session_scope).
- External call phai co timeout va error message ro.

## 4. Chat async architecture
- ChatHandler (async mode) -> DispatcherService.dispatch_chat_request.
- DispatcherService -> RedisQueueService.enqueue.
- ChatWorkerService -> RedisQueueService.dequeue -> processor(payload) theo thu tu FIFO.

## 5. Sync-doc architecture
- SyncDocumentModuleImpl goi chain service:
	DocumentService -> GeminiOCRService -> DatabaseSyncService -> VectorDBService.

## 6. Naming va import
- Dung duong dan import hien tai, khong dung ten cu nhu vector_db_services hoac ocr_service.
