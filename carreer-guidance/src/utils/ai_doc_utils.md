# Utils Layer Spec

## 1. Scope
Folder: src/utils/
Noi chua utility dung chung, khong chua business orchestration.

## 2. Hien tai
- src/utils/api_response/*: wrapper response Ok, BadRequest, NotFound, InternalServerError, ...

## 3. Rule
- Utility phai stateless, de test.
- Error message huong user can de hieu nhung khong lo thong tin nhay cam.
- Moi utility moi can typed ro rang va ten de doan duoc hanh vi.
