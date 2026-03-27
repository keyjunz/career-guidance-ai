# Handler Layer Spec

## 1. Scope
Folder: src/handlers/
Handler la boundary orchestrator giua route va business layer.

## 2. Files hien tai
- src/handlers/chat_handler.py
- src/handlers/sync_doc_handler.py

## 3. ChatHandler contract
Class ChatHandler:
- __init__(execution_id)
- execute(request, invocation_type)
- invoke_async_chat_handler(request)
- invoke_sync_chat_handler(request)
- stream_tokens(request)

Rule:
- invocation_type="async" chi enqueue vao queue (qua DispatcherService).
- invocation_type="sync" process ngay qua agent_main.invoke.
- stream_tokens dung invoke_stream va tra token async iterator.

## 4. SyncDataHandler contract
Class SyncDataHandler:
- __init__(execution_id)
- handle_sync_data(body, context)
- handle_get_sync_data_status(params)

Rule:
- Body parser chap nhan model, json string, dict.
- Goi SyncDocumentModuleImpl cho submit va status.
- Khong co in-memory status store.

## 5. Rule chung
- Khong su dung base_handler/dataclass protocol runtime layer da bo.
- Khong query DB truc tiep o handler.
- Khong call OCR/Redis truc tiep o handler.
- execution_id phai truyen xuong module/service.
