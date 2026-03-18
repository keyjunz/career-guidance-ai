# 🤖 RAG Chatbot (Retrieval-Augmented Generation)

Đây là module RAG Pipeline cốt lõi cho dự án AI Chatbot chuyên ngành Computer Science. Hệ thống được thiết kế tối ưu để có thể chạy trên phần cứng cá nhân hạn chế (như GTX 1650 4GB) bằng cách kết hợp sức mạnh tìm kiếm cục bộ và khả năng sinh văn bản (Generation) từ các LLM API miễn phí (Groq/Gemini).

## 🌟 Tính Năng Nổi Bật

- **Hybrid Search (Tìm kiếm Lai):** Kết hợp FAISS (Semantic Search bằng vector) và BM25 (Keyword Search) qua thuật toán Reciprocal Rank Fusion (RRF) để ra kết quả chính xác nhất.
- **Cross-Encoder Reranking:** Sử dụng `ms-marco-MiniLM` để chấm điểm lại mức độ phù hợp của tài liệu so với câu hỏi (chạy cực nhẹ trên CPU/GPU local).
- **API LLM Integration:** Hỗ trợ gọi API tới **Groq** (Llama-3-70B) và **Google Gemini** thay vì chạy mô hình nặng trên máy, giảm độ trễ (latency) từ vài chục phút xuống dưới **1 giây**.
- **Đa Ngôn Ngữ:** Hỗ trợ hỏi đáp bằng cả Tiếng Anh và Tiếng Việt.

---

## 🎯 Đánh Giá Mức Độ Hoàn Thành Kế Hoạch (For Leader/Manager)

Dưới đây là phần đối chiếu giữa **Bản Kế Hoạch Yêu Cầu Gốc** và thực tế mã nguồn đã hoàn thiện 100% trong dự án:

| Task Gốc | Hạng Mục | Trạng Thái | Chi Tiết Thành Quả Trong Code |
|---|---|---|---|
| **1.3** | **Implement Embedding** | ✅ Hoàn Thành | - Dùng model `multilingual-e5-small`.<br>- Có hàm `encode_query` & `encode_passages` (chạy batch).<br>- Tích hợp bộ đệm lưu Cache (MD5 hashing) ngay trên ổ cứng giúp siêu tiết kiệm sức mạnh tính toán. |
| **1.4** | **Query (Vector Search)** | ✅ Hoàn Thành | - Phiên dịch câu hỏi (Query) thành dạng số (Embedding vector).<br>- Thực hiện Hybrid Search chạy song song FAISS và BM25 chặn bắt Top 20 tài liệu liên quan nhất. |
| **1.5** | **Implement Rerank** | ✅ Hoàn Thành | - Dùng Cross-Encoder `ms-marco-MiniLM-L-6-v2`.<br>- Nhận Top 20 từ Search, cho AI đọc và cho điểm lại (Relevance Score), hất văng tài liệu nhiễu và đóng gói đúng Top 5 xịn nhất gửi đi. |
| **1.6** | **Implement Generation** | ✅ Hoàn Thành | - LLM tích hợp được cả Qwen cục bộ lẫn **API mây siêu tốc (Groq/Gemini)**.<br>- Quản lý cấu trúc Prompt (đã inject context).<br>- Quản lý nghẽn bộ nhớ bằng cách chặt Token cứng (512 token ở Input, `MAX_ANSWER_WORDS` ở Output).<br>- Code thêm tính năng **Tự động thử lại (Retry 3 lần có độ trễ)** khi gọi API tránh lỗi mạng. |
| **1.7** | **RAG Pipeline** | ✅ Hoàn Thành | - Ghép đủ 6 khối mắt xích thành một file hệ thống `rag_pipeline.py`. Chỉ bằng 1 lệnh gọi là chạy Auto từ A đến Z. |

---

## 🛠 Cài Đặt Ban Đầu

**1. Tạo môi trường Conda**
```bash
conda create -n rag310 python=3.10
conda activate rag310
```

**2. Cài đặt Python packages**
```bash
pip install -r requirements.txt
```

**3. Cấu hình API Key**
Copy file `.env.example` thành file `.env` và điền khóa API của bạn vào:
```env
GROQ_API_KEY=gsk_your_key_here
GEMINI_API_KEY=AIzaSy_your_key_here
```

---

## 🚀 Hướng Dẫn Sử Dụng

Quy trình chuẩn bị dữ liệu và chạy Bot bao gồm 3 bước:

### Bước 1: Thu thập & Chia nhỏ Dữ Liệu (Data Crawling)
Lấy dữ liệu từ Wikipedia và arXiv, sau đó cắt nhỏ (chunking) thành tài liệu 512 tokens:
```bash
python data_crawler.py
```
*(Đầu ra: `data/chunks.json`)*

### Bước 2: Xây Dựng Vector DB (Indexing)
Tính toán Vector Embedding cho tất cả các tài liệu và lưu thành Database:
```bash
python build_vectordb.py --backend faiss
```
*(Đầu ra: Thư mục `indexes/` chứa cấu trúc tri thức)*

### Bước 3: Chạy RAG Chatbot!
Hỏi một câu đơn lẻ (kết hợp Groq API để siêu nhanh):
```bash
python rag_pipeline.py --query "question?" --use-api --api-model groq-llama3-70b
```

Hoặc bật chế độ Chat tương tác liên tục:
```bash
python rag_pipeline.py --interactive --use-api --api-model groq-llama3-70b
```

---

## 📊 Đánh Giá Đóng Gói (Benchmarking & Evaluation)

### 1. Benchmark (Đo Hiệu Năng Tốc Độ / Bộ Nhớ)
Đo xem mỗi cục xử lý (Embedding, Retriever, Reranker, LLM) tốn bao nhiêu mili-giây và bao nhiêu RAM:
```bash
# Đo Embedding
python benchmark.py --component embedding

# Đo Retriever (FAISS + BM25)
python benchmark.py --component retriever

# Đo tốc độ chấm điểm lõi
python benchmark.py --component reranker

# Đo tốc độ của LLM local
python benchmark.py --component llm

# Đo toàn bộ pipeline (Full)
python benchmark.py --component full
```

### 2. Evaluation (Đo Chất Lượng Trả Lời)
Hệ thống có một tập câu hỏi test (Tự sinh hoặc tự soạn). Script này đo điểm số BLEU, ROUGE-L (độ khớp với đáp án mẫu) và **Tỉ lệ Ảo giác (Hallucination Rate)** (xem AI có bịa thông tin lố so với tài liệu gốc không).

```bash
# Tạo bộ test data (20c hỏi) tự động (nếu chưa có)
python evaluate.py --create-dataset

# Chạy chấm điểm
python evaluate.py --max-questions 10
```

### 3. A/B Testing (So sánh Model)
Nếu bạn muốn thử xem model nhúng `all-MiniLM-L6-v2` có tốt hơn `multilingual-e5-small` hay không:
```bash
python ab_testing.py --test embedding
```

---
*Thuộc dự án RAG Core System - AI Agent.*
