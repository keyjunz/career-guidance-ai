# Request Body Layer Spec

## 1. Scope
Folder: src/request_body/
Dinh nghia schema request/response cho API boundary.

## 2. Sync-doc schema rules
- SyncDocumentsRequest: user_id, file_urls, download_dir(optional).
- Validate moi URL bat dau bang http:// hoac https://.
- SyncDocumentsResponse: job_id, status, processed, failed, downloaded.
- status chi hop le voi 4 gia tri workflow.

## 3. Chat schema rules
- Ho tro multi-modal content item.
- Validate message/image_url theo contract.

## 4. General rules
- Dung Pydantic v2, validators ro rang.
- Khong chua business logic.
