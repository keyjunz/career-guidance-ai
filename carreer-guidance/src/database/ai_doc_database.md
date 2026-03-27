# Database Layer Spec

## 1. Scope
Folder: src/database/
Chua SQLAlchemy base va models persistence.

## 2. Folder structure
- src/database/base.py
- src/database/models/*

## 3. Sync-doc data rule
- Document model luu ingestion_job_id va status.
- status hop le: start, processing, failed, completed.
- Polling status phai dua tren du lieu DB, khong fallback local memory.

## 4. Transaction boundary
- Service/repository la noi thao tac transaction.
- Khong thao tac session truc tiep trong route/handler/module.

## 5. Migration
- Alembic version phai dong bo voi model hien tai.
- Moi thay doi schema can kem migration upgrade/downgrade ro rang.
