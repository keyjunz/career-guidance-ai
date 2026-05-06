# Frontend - Career Guidance AI

Frontend su dung React + TypeScript + Vite.

## 1) Cai dat va chay local

```powershell
cd frontend
npm install
npm run dev
```

Mac dinh FE chay tai `http://localhost:5173`.

## 2) Cau hinh API base url

Tao file `.env` tu `.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Luu y: backend can chay truoc va dung host/port trong bien nay.

## 3) Luong test co ban (auth + chat)

1. Mo FE (`/login`)
2. Dang ky account moi tai `/register` (hoac login bang account co san)
3. Login thanh cong se redirect sang `/chat`
4. Gui cau hoi tren chat

Frontend da duoc rap API that:

- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `POST /api/chat?invocation_type=sync`

## 4) Build/Lint

```powershell
npm run lint
npm run build
```

## 5) Ghi chu

- Neu backend tra `401`, hay login lai de lay access token moi.
- Neu chat tra loi lien quan ChromaDB connection, do la van de hạ tang BE/vector store, khong phai loi UI.
