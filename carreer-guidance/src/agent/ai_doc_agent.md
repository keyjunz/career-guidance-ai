# Agent Layer Spec

## 1. Scope
Folder: src/agent/
Agent phuc vu chat orchestration. Khong can tham gia sync-document pipeline.

## 2. Rules
- Dung typed state ro rang.
- Co trace_id/execution_id trong state de observability.
- Tool calls phai qua module/service contracts, khong call DB truc tiep.

## 3. Constraints lien quan workflow chung
- Khong anh huong sync-doc status model.
- Khong chia se business session_id cho sync-doc.
- Neu can luu hoi thoai, dung conversation/session domain rieng cua chat.

## 4. Quality
- Co fallback khi tool fail.
- Khong hallucinate sources.
- Co guard retry de tranh loop vo han.
