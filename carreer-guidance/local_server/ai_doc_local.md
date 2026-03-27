# Local Server Layer Spec

## 1. Scope
Folder: local_server/
Layer nay chi la HTTP boundary cua FastAPI.

## 2. Files chinh
- local_server/main.py: create app, middleware trace_id, global exception handler.
- local_server/routes/chat/router.py: chat sync, chat async enqueue, stream SSE.
- local_server/routes/sync_doc/router.py: submit sync-doc job va poll status.

## 3. Rule chung
- Route phai async (phu hop FastAPI).
- Route chi parse request, tao context, goi handler, map response util.
- Dung src/utils/api_response cho output payload.
- Khong dat business logic OCR/chunking/DB update trong route.

## 4. Chat endpoint contract
- POST /api/chat?invocation_type=sync|async
- sync: goi ChatHandler.execute(..., "sync") de process ngay.
- async: goi ChatHandler.execute(..., "async") de enqueue vao Redis qua DispatcherService.
- POST /api/chat/stream: stream token SSE tu ChatHandler.stream_tokens.

## 5. Sync endpoint contract
- POST /api/sync-documents: goi SyncDataHandler.handle_sync_data.
- GET /api/sync-documents/{job_id}: goi SyncDataHandler.handle_get_sync_data_status.
- status chi doc tu DB, khong dung in-memory fallback.

## 6. Tracing va error
- x-trace-id middleware duoc set trong request.state.trace_id.
- trace_id duoc propagate thanh execution_id.
- ValueError map ve bad request, cac loi con lai map internal server error.
