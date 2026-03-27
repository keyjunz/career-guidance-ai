# Master Implementation Guide

## 1. Muc tieu
Tai lieu nay la index tong de dieu huong code trong thu muc carreer-guidance.
Muc tieu: moi thanh vien nam ro boundaries, contracts, va workflow hien tai.

## 2. Kien truc tong
- local_server: HTTP boundary (FastAPI router + middleware).
- handlers: parse request, goi module/service, map response.
- modules: business orchestration.
- services: implementation va external I/O (Gemini, Redis, filesystem, DB session usage).
- repositories: query/persistence abstraction.
- database: SQLAlchemy model + migration.

## 3. Workflow chuan
### 3.1 Chat
- Sync mode: route -> ChatHandler.invoke_sync_chat_handler -> agent invoke.
- Async mode: route -> ChatHandler.invoke_async_chat_handler -> DispatcherService -> Redis queue.
- Worker mode: ChatWorkerService dequeue va process tung message theo kieu sync.

### 3.2 Sync document
- route -> SyncDataHandler -> SyncDocumentModuleImpl -> services.
- DB status dung 4 gia tri: start, processing, failed, completed.
- trace_id middleware chinh la execution_id business.

## 4. Rule bat buoc
- Router khong chua business logic.
- Handler khong goi DB/OCR truc tiep.
- Module khong goi external API truc tiep.
- Service nhan execution_id qua constructor.
- DB session chi dung trong service/repository boundary bang context manager.

## 5. Danh muc huong dan theo thu muc
- local_server/ai_doc_local.md
- src/config/ai_doc_config.md
- src/database/ai_doc_database.md
- src/repositories/ai_doc_repositories.md
- src/request_body/ai_doc_request_body.md
- src/handlers/ai_doc_handler.md
- src/modules/ai_doc_module.md
- src/services/ai_doc_services.md
- src/agent/ai_doc_agent.md
- src/prompts/ai_doc_prompt.md
- src/utils/ai_doc_utils.md

## 6. Definition of done
- Tinh nhat quan boundaries duoc giu vung.
- Khong con import/cu phap cu (base_handler, DomainError protocol runtime da bo).
- execution_id duoc truyen thong suot va log duoc.
- Doc update phan anh dung code hien tai.
