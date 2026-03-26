# Module Layer Spec

## 1. Scope
Folder: src/modules/
Module la orchestration layer cho business flow. Khong chua implementation chi tiet.

## 2. Sync document module bat buoc
Folder: src/modules/sync_doc_module/
Trong class SyncDocumentModuleImpl chi duoc ton tai dung 3 methods:
- __init__
- sync_documents
- get_status_sync_doc

## 3. Service delegation rules
- OCR phai goi src/services/gemini/ocr_service.py
- Document prepare/chunk phai goi src/services/document_service.py
- DB status/job phai goi src/services/database_service.py
- Vector DB phai goi src/services/vector_db_services.py
- Khong define service class moi trong module.

## 4. Sync workflow contract
- sync_documents(request, context):
  - tao job status start
  - update processing
  - run prepare -> ocr -> chunk -> upsert
  - ket thuc completed hoac failed
- get_status_sync_doc(job_id, context):
  - tra SyncDocumentsResponse theo DB status

## 5. Status va tracing
- Chi dung: start | processing | failed | completed.
- execution_id = context.trace_id, truyen xuong service.
- Khong su dung business session_id trong sync summary.

## 6. Error rules
- Module catch exception de cap nhat failed neu can.
- Raise DomainError da map hoac map tai boundary phu hop.
