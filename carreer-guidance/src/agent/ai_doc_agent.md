# Agent Layer Spec

## 1. Scope
Folder: src/agent/
Agent la runtime xu ly chat logic khi ChatHandler chay sync mode.

## 2. Integration point
- ChatHandler.invoke_sync_chat_handler goi src.agent.main.invoke.
- ChatHandler.stream_tokens goi src.agent.main.invoke_stream.

## 3. Rule
- Agent phai ton trong execution_id tu context.
- Khong duoc can thiep workflow sync-document status.
- Neu dung tool, phai qua module/service boundary, tranh query DB truc tiep.

## 4. Ghi chu hien tai
- src/agent/main.py dang la diem neo interface.
- Khi implement chi tiet, giu nguyen contract invoke/invoke_stream de khong vo ChatHandler.
