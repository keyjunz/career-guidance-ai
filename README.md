# Career Guidance AI

Career Guidance AI la du an tro ly huong nghiep su dung AI, ho tro hoi dap theo boi canh nguoi dung va mo rong voi cac module nhu RAG va dong bo tai lieu.

## Setup backend

Version de xuat: Python 3.10+ (da test on Windows voi conda env).

### 1) Di chuyen vao backend

```powershell
cd carreer-guidance
```

### 2) Tao/kich hoat moi truong ao

```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
```

### 3) Cai thu vien

```powershell
pip install -r requirements.txt
```

### 4) Cau hinh `.env`

Copy tu `.env.example` va dien gia tri that.

Luu y quan trong:

- `DATABASE_URL` nen dung sync PostgreSQL driver:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/career_guidance
```

- Neu muon su dung RAG/sync day du, can cau hinh ChromaDB dung mode/port dang chay.

### 5) Migration database

```powershell
alembic upgrade head
alembic current
```

### 6) Chay local server

```powershell
uvicorn local_server.main:app --reload --host 127.0.0.1 --port 8000
```

Neu port 8000 bi chiem, doi sang port khac (vd: 8010).

### 7) Kiem tra server

- Healthcheck: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Auth quick test

1. `POST /api/auth/login` de lay `access_token`
2. Bấm `Authorize` trong Swagger (HTTP Bearer), dan token
3. Test `GET /api/auth/me`

Note:

- `GET /api/auth/me` se tra `401 Not authenticated` neu khong gui Bearer token.
- Neu token het han, cac API protected (admin/sync) se tra `401 Could not validate credentials`.

## Chat quick test

Dung body:

```json
{
  "question": "hello, ban giup gi duoc cho toi?"
}
```

`user_id` khong can gui tu client (duoc inject tu JWT trong server).

## Sync/RAG note

Neu gap loi ket noi ChromaDB nhu:

`Cannot connect to ChromaDB at localhost:8001`

thi day la loi ha tang vector store, khong phai loi auth/request body.

Can dam bao:

- Chroma server dang chay dung host/port trong `.env`, hoac
- Cau hinh mode persistent phu hop voi may local.
