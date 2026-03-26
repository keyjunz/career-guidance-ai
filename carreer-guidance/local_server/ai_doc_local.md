# Local Server Layer Spec

## 1. Scope
Folder: local_server/
Layer nay chi la HTTP boundary. Khong chua business logic.

## 2. Files chinh
- local_server/main.py: tao app, middleware, exception mapping, include routers.
- local_server/routes/chat/router.py: endpoint chat.
- local_server/routes/sync_doc/router.py: endpoint sync-doc submit + poll status.

## 3. Rules
- Route duoc async de phu hop FastAPI.
- Route chi lam 4 viec: nhan request, tao RequestContext, goi handler, map response util.
- Dung src/utils/api_response cho tat ca response.
- Khong de queue/in-memory status cho sync flow neu da co DB status.

## 4. Sync endpoints contract
- POST /api/sync-documents:
  - Nhap SyncDocumentsRequest.
  - Tao context chua trace_id (execution_id).
  - Goi SyncDataHandler.handle_sync_data(...).
  - Tra ve SyncDocumentsResponse theo response util.
- GET /api/sync-documents/{job_id}:
  - Goi SyncDataHandler.handle_get_sync_data_status(...).
  - Tra ve status tu module/service DB, khong doc local dict.

## 5. Error mapping
- DomainError BAD_REQUEST -> 400.
- DomainError NOT_FOUND -> 404.
- DomainError khac -> 500.
- Unknown error -> InternalServerError.

## 6. Logging
- Log theo trace_id tu middleware.
- Khong setup logger config trong route file.
