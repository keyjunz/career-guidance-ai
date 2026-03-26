# Database Layer Spec

## 1. Scope
Folder: src/database/
Dinh nghia models, metadata, migrations.

## 2. Sync-doc lien quan
- Document model phai co ingestion_job_id + status.
- Status luu bo 4 gia tri workflow: start, processing, failed, completed.

## 3. Transaction boundary
- CRUD thong qua repositories/service.
- Dung sync session context manager.
- Khong su dung async SQLAlchemy cho core flow.

## 4. Migration
- Co init schema va downgrade hop le.
- Index cho ingestion_job_id va cac truong truy van thuong xuyen.
