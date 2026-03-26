# Config Layer Spec

## 1. Scope
Folder: src/config/
Quan ly app settings va DB config.

## 2. Rules
- Moi cau hinh den tu environment.
- Settings typed va validate fail-fast.
- DB session factory cho sync flow.

## 3. Session va execution_id rule
- Session o day chi la DB session context manager.
- Khong tao APP_SESSION_ID cho sync business.
- execution_id la runtime context, khong dat co dinh trong settings.

## 4. Required outputs
- settings.py: Settings singleton.
- database.py: engine, SessionLocal, get_session/session_scope.
