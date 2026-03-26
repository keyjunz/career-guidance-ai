# Prompt Layer Spec

## 1. Scope
Folder: src/prompts/
Quan ly prompt templates cho chat/rag/evaluator/fixer.

## 2. Rules
- Prompt phai typed input/output ro rang.
- Co anti-hallucination rule: khong du du lieu thi noi khong du du lieu.
- Tach system prompt va task prompt.

## 3. Python template safety
- Khong dung str.format truc tiep voi template co JSON braces.
- Uu tien replace placeholder an toan hoac escape braces.

## 4. Versioning
- Moi prompt quan trong co version id.
- Co changelog ngan khi thay doi behavior.
