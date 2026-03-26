# Config Layer Spec

## 1. Scope
Folder: src/config/
Quan ly toan bo runtime settings va DB session factory.

## 2. Files
- settings.py
- database.py

## 3. settings.py contract
- Su dung pydantic-settings, env_file=.env.
- Gom cac nhom: app, db, llm, vector_store, redis, web_search.
- validate_startup_config fail-fast neu thieu env hoac sai value.

## 4. database.py contract
- create_engine_from_settings cho SQLAlchemy sync engine.
- get_session_factory cache bang lru_cache.
- session_scope context manager commit/rollback.
- get_session cho dependency injection khi can.

## 5. Rule chung
- execution_id khong duoc hardcode trong config.
- DB session chi tao/quan ly tai config + service boundary.
