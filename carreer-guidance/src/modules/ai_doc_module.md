# Module Layer Spec

## 1. Scope
Folder: src/modules/
Module la orchestration business flow, khong chua implementation external I/O.

## 2. Sync document module
Folder: src/modules/sync_doc_module/
Class: SyncDocumentModuleImpl

Method:
- __init__(execution_id, ...service overrides)
- sync_documents(request, context)
- get_status_sync_doc(ingestion_job_id, context)

## 3. Delegation bat buoc
- Download + chunk: DocumentService.
- OCR: GeminiOCRService.
- Status job DB: DatabaseSyncService.
- Chunk archive/upsert: VectorDBService.

## 4. Luong sync_documents
1. Validate context.trace_id khop execution_id.
2. Create sync job (status start).
3. Update processing.
4. prepare_documents -> extract_text_batch -> apply_ocr_results -> chunk_documents -> upsert_chunks.
5. Mark completed hoac failed.
6. Tra SyncDocumentsResponse.

## 5. Rule chung module
- Module duoc phep orchestration theo thu tu, nhung khong goi truc tiep DB session hoac HTTP client.
- execution_id phai di xuyen suot.
- Neu exception xay ra sau khi tao job thi phai mark_failed.
