# Handler Layer Spec

## 1. Scope
Folder: src/handlers/
Handlers la boundary orchestrator, khong chua business implementation.

## 2. Required files
- src/handlers/base_handler.py
- src/handlers/chat_handler.py
- src/handlers/sync_doc_handler.py

## 3. base_handler.py contract
- RequestContext dataclass: trace_id, user_id.
- DomainError: code, message, details(optional).
- map_exception_to_domain_error(exc) -> DomainError.

## 4. chat_handler.py contract
- handle_chat(request, context, chatbot) -> ChatResponse.
- handle_chat_stream(request, context, chatbot) -> AsyncIterator[str].
- Chi map error, khong viet chat logic tai handler.

## 5. sync_doc_handler.py contract
Class SyncDataHandler chi duoc co dung 3 methods:
- __init__
- handle_sync_data
- handle_get_sync_data_status

Rules:
- Parse body linh hoat (model|string|dict) trong handle_sync_data.
- Goi sync_document_module.sync_documents(...) cho submit flow.
- Goi sync_document_module.get_status_sync_doc(...) cho polling flow.
- Khong dung in-memory status store trong handler.
- Khong stub business flow cho production path.

## 6. Global rules
- execution_id = context.trace_id, di xuyen suot qua module/service.
- Khong tao va khong truyen business session_id trong sync flow.
- Dung api_response util tai route layer.
