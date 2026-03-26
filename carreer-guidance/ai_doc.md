# Master Implementation Guide

## 1. Vai tro
Ban dong vai tro AI coder cho backend system theo clean architecture va workflow sync-doc da chot.
Muc tieu: code dung boundaries, dung contract, dung thu tu layer.

## 2. Architecture bat buoc
- local_server: HTTP boundary (FastAPI route).
- handlers: orchestration sat boundary, map input/output/error.
- modules: business orchestration theo luong sync.
- services: implementation thuc te (OCR, DB, vector DB, archive, LLM).
- repositories: persistence abstraction.
- database: SQLAlchemy model + migration.

## 3. Workflow phai tuan thu
- Chat: route async, handler async, module co the async/sync tuy contract hien tai.
- Sync document: route co the async boundary, nhung flow xu ly business phai sync trong handler/module/service.
- Status sync chi duoc dung 4 gia tri: start, processing, failed, completed.
- execution_id phai di xuyen suot route -> handler -> module -> service.
- Session DB chi duoc su dung trong context manager tai tang DB/service (`with session_scope()` hoac `with get_session() as session`).

## 4. Quy tac coding
- Khong dat business logic trong route.
- Khong goi truc tiep DB/OCR/LLM tai handler.
- Khong goi external API truc tiep tai module, phai qua service.
- Type hints day du, model typed ro rang.
- Error map ve DomainError o handler boundary.

## 5. Thu tu implementation
1. Cap nhat tai lieu ai_doc_*.
2. Cap nhat handlers theo workflow.
3. Cap nhat route de dung handler contracts.
4. Cap nhat module/service neu contract thay doi.
5. Chay check loi va test luong chinh.

## 6. Definition of done
- Khong con pending trong sync status.
- Khong con stub bat buoc cho sync flow production path.
- execution_id hien dien trong log/context toan bo sync flow.
- Khong su dung session_id nghiep vu trong sync summary.
