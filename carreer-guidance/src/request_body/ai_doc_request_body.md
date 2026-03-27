# Request Body Layer Spec

## 1. Scope
Folder: src/request_body/
Chua Pydantic schemas cho API boundary.

## 2. Sync-doc schemas
- SyncDocumentsRequest: user_id, file_urls, download_dir.
- file_urls phai bat dau bang http:// hoac https://.
- SyncDocumentsResponse: job_id, status, processed, failed, downloaded.

## 3. Chat schemas
- ChatRequest: user_id, message, image_url, conversation_id.
- ChatResponse: type, content, conversation_id, trace_id.
- ContentItem validate theo type=text|image.

## 4. Common schema
- ErrorResponse cho global exception output.

## 5. Rule chung
- Pydantic v2, extra=forbid.
- Schema chi validate input/output, khong chua orchestration logic.
