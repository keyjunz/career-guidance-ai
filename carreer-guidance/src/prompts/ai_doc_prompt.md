# Prompt Layer Spec

## 1. Scope
Folder: src/prompts/
Quan ly prompt templates cho chat va cac module mo rong.

## 2. Rule
- Tach system prompt va task prompt.
- Prompt phai ro input/output ky vong.
- Neu khong du du lieu, model phai tra loi trung thuc ve muc do khong chac chan.

## 3. Template safety
- Khong dung str.format truc tiep cho template co JSON braces.
- Uu tien replace placeholder hoac escape braces de tranh KeyError.

## 4. Versioning
- Prompt quan trong nen co version id hoac comment version.
- Khi doi behavior lon, cap nhat changelog ngan trong file.
