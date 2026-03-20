# 🤖 RAG Chatbot (Retrieval-Augmented Generation)

Đây là module RAG Pipeline cốt lõi cho dự án AI Chatbot chuyên ngành Computer Science. Hệ thống được thiết kế tối ưu để có thể chạy trên phần cứng cá nhân hạn chế bằng cách kết hợp sức mạnh tìm kiếm cục bộ và khả năng sinh văn bản (Generation) từ các LLM API miễn phí (Groq/Gemini).

---

## 🎯 Mức Độ Hoàn Thành Kế Hoạch

| Task Gốc | Hạng Mục | Trạng Thái | Chi Tiết Thành Quả Trong Code |
|---|---|---|---|
| **1.3** | **Implement Embedding** | ✅ Hoàn Thành | - Dùng model `multilingual-e5-small`.<br>- Có hàm `encode_query` & `encode_passages` (chạy batch).<br>- Tích hợp bộ đệm lưu Cache (MD5 hashing) ngay trên ổ cứng giúp siêu tiết kiệm sức mạnh tính toán. |
| **1.4** | **Query (Vector Search)** | ✅ Hoàn Thành | - Phiên dịch câu hỏi (Query) thành dạng số (Embedding vector).<br>- Thực hiện Hybrid Search chạy song song FAISS và BM25 chặn bắt Top 20 tài liệu liên quan nhất. |
| **1.5** | **Implement Rerank** | ✅ Hoàn Thành | - Dùng Cross-Encoder `ms-marco-MiniLM-L-6-v2`.<br>- Nhận Top 20 từ Search, cho AI đọc và cho điểm lại (Relevance Score), hất văng tài liệu nhiễu và đóng gói đúng Top 5 xịn nhất gửi đi. |
| **1.6** | **Implement Generation** | ✅ Hoàn Thành | - LLM tích hợp được cả Qwen cục bộ lẫn **API mây siêu tốc (Groq/Gemini)**.<br>- Quản lý cấu trúc Prompt (đã inject context).<br>- Quản lý nghẽn bộ nhớ bằng cách chặt Token cứng (512 token ở Input, `MAX_ANSWER_WORDS` ở Output).<br>- Code thêm tính năng **Tự động thử lại (Retry 3 lần có độ trễ)** khi gọi API tránh lỗi mạng. |
| **1.7** | **RAG Pipeline** | ✅ Hoàn Thành | - Ghép đủ 6 khối mắt xích thành một file hệ thống `rag_pipeline.py`. Chỉ bằng 1 lệnh gọi là chạy Auto.<br>- **Mới:** Tích hợp tự động nhận diện ngôn ngữ (VI/EN) giúp người dùng chat tự nhiên không cần chuyển đổi thủ công. |

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
Hệ thống mặc định sử dụng Groq API (Llama 3 70B) để đảm bảo tốc độ và độ chính xác cao nhất.

Hỏi một câu đơn lẻ:
```bash
python rag_pipeline.py --query "Mạng nơ-ron nhân tạo là gì?"
```

Hoặc bật chế độ Chat tương tác liên tục (Khuyên dùng):
```bash
python rag_pipeline.py --interactive
```

> [!TIP]
> **Tính năng Auto-Language:** Bạn có thể hỏi bằng cả Tiếng Việt và Tiếng Anh. Hệ thống sẽ tự động nhận diện, dịch câu hỏi (nếu cần) và trả lời đúng ngôn ngữ bạn sử dụng.

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
# Tạo bộ test data (tự động 12 câu) từ dữ liệu bot
python evaluate.py --create-dataset --max-questions 12

# Chạy chấm điểm
python evaluate.py --max-questions 12
```

**Kết quả đánh giá thực tế của hệ thống(Bộ câu hỏi test được tạo từ corpus gốc bởi LLM do Groq cung cấp giống với LLM dùng để trả lời):**
- **Avg BLEU:** 27.19 ✅ (Vượt ngưỡng 25. Trả lời khá chuẩn xác so với đáp án gốc)
- **Avg ROUGE-L:** 54.16 ✅ (Vượt ngưỡng 40. Bám sát ý chính, diễn đạt tốt)
- **Hallucination Rate:** 0.0% ✅ (Mức ảo giác bằng 0. Hoàn toàn phụ thuộc vào ngữ cảnh được cung cấp, không bịa đặt)
- **Avg Latency:** 6383ms (Đã bao gồm: 50% thời gian Embedding/Retrieval và 50% thời gian gọi Groq API sinh câu trả lời)

---
*Thuộc dự án RAG Core System - AI Agent.*
