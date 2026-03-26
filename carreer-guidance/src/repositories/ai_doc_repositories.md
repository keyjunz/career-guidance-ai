# Repository Layer Spec

## 1. Scope
Folder: src/repositories/
Repository cach ly SQL/query khoi business logic.

## 2. Rules
- Tat ca repository methods la sync.
- Nhan Session da duoc quan ly boi service/context manager.
- Khong commit/rollback tung method nho tru khi co ly do dac biet.

## 3. Required capabilities
- Generic CRUD base.
- DocumentRepository co get_by_ingestion_job_id cho sync-doc polling.
- Methods list co pagination cho tap du lieu lon.

## 4. Boundaries
- Khong map HTTP error o repository.
- Khong chua orchestration flow.
