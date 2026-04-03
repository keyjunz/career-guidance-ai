# Career Guidance AI

Career Guidance AI la du an tro ly huong nghiep su dung AI, ho tro hoi dap theo boi canh nguoi dung va mo rong duoc voi cac module nhu RAG, web search, sinh anh va dong bo tai lieu.

## Setup va chay du an
Version: python 3.11.*
### Create .env:
    Giong voi .env.example 
### 1. Di chuyen vao thu muc backend
```powershell
cd carreer-guidance
```

### 2. Tao va kich hoat moi truong ao
```powershell
py -3 -m venv .venv
.\.venv\Scripts\activate
```

### 3. Cai dat thu vien can thiet
```powershell
pip install -r requirements.txt
```

### 4. Setup database tu migration version co san
#### 4.1 Tao database PostgreSQL
```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE career_guidance;"
```

#### 4.2 Cau hinh DATABASE_URL trong file .env
Vi du cho sync driver:
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/career_guidance
```

#### 4.3 Chay migration tu version co san
Migration init da co san trong thu muc alembic/versions (revision 20260326_0001).
```powershell
alembic upgrade head
```

#### 4.4 Kiem tra version migration hien tai
```powershell
alembic current
```

Neu gap loi thieu driver psycopg2:
```powershell
pip install psycopg2-binary
```

### 5. Chay local server
```powershell
uvicorn local_server.main:app --reload --host 127.0.0.1 --port 8010
```

### 6. Kiem tra server
- Healthcheck: `http://127.0.0.1:8010/health`
- Swagger UI: `http://127.0.0.1:8010/docs`

