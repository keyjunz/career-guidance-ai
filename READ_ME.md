# Career Guidance AI

He thong tu van huong nghiep bang AI, ho tro chat va dong bo tai lieu OCR.

## 1. Muc tieu san pham
- Tra loi cau hoi huong nghiep ro rang, co can cu, an toan.
- Goi y nganh hoc dua tren diem hoc tap, so thich, ky nang, dieu kien tai chinh, muc tieu nghe nghiep.
- Co kha nang mo rong de them cong cu ho tro (OCR, crawl, recommendation, analytics).

## 2. Kien truc tong quan
- API layer: FastAPI (local_server/).
- Handler layer: parse/map request-response (src/handlers/).
- Module layer: orchestration business flow (src/modules/).
- Service layer: Gemini OCR, Redis dispatcher/worker, document pipeline, DB status (src/services/).
- Data layer: SQLAlchemy + repositories (src/database/, src/repositories/).
- Prompt layer: templates va conventions (src/prompts/).

## 3. Cac tai lieu huong dan code theo tung thu muc

- carreer-guidance/ai_doc.md
- carreer-guidance/local_server/ai_doc_local.md
- carreer-guidance/src/config/ai_doc_config.md
- carreer-guidance/src/database/ai_doc_database.md
- carreer-guidance/src/repositories/ai_doc_repositories.md
- carreer-guidance/src/request_body/ai_doc_request_body.md
- carreer-guidance/src/handlers/ai_doc_handler.md
- carreer-guidance/src/modules/ai_doc_module.md
- carreer-guidance/src/services/ai_doc_services.md
- carreer-guidance/src/agent/ai_doc_agent.md
- carreer-guidance/src/prompts/ai_doc_prompt.md
- carreer-guidance/src/utils/ai_doc_utils.md

## 3.1 Danh muc hinh so do he thong
Nguoi doc (va AI coder) nen xem cac hinh nay truoc khi implement:
- `carreer-guidance/image-3.png`: use case tong quan.
- `carreer-guidance/image-1.png`: function overview.
- `carreer-guidance/image.png`: chat workflow.
- `carreer-guidance/image-2.png`: sync workflow.
- `carreer-guidance/src/agent/image-1.png`: so do agent.
- `carreer-guidance/src/database/image.png`: so do database/ERD.

Luu y:
- Moi hinh trong tai lieu phai co chu thich 1-2 dong ve muc dich.
- Khi them hinh moi, cap nhat danh muc nay de AI coder tim duoc ngay.

## 4. Thu tu implement khuyen nghi
1. Cap nhat docs trong ai_doc*.md neu doi kien truc.
2. Chinh route -> handler -> module -> service theo boundaries.
3. Kiem tra flow chat sync/async va worker dequeue.
4. Kiem tra flow sync-document va polling status.
5. Chay error check truoc khi merge.

## 5. Definition of Done
- API khoi dong thanh cong bang Uvicorn.
- Swagger co day du schema va example.
- Chat flow chay duoc voi RAG va fallback web search.
- Co luu vung hoi thoai/message/cost log vao DB.
- Co migration up/down duoc.
- Log co trace_id va error code.
- Co toi thieu unit test cho service/module quan trong.

## 6. Prompt tong de giao cho AI coder
"Read ai_doc.md and all ai_doc_*.md files first. Implement strictly by folder boundaries: route -> handler -> module -> service -> repository/database. Keep execution_id propagation and preserve chat async enqueue + sync worker processing model."

