# RAG Module (Retrieval-Augmented Generation)

Module này đảm nhiệm luồng xử lý RAG hoàn chỉnh cho hệ thống AI của Career Guidance, bao gồm:
1. Nhận câu hỏi
2. Tư động nhận diện ngôn ngữ và dịch (Vi -> En) nếu cần để giúp tối ưu hóa việc tìm kiếm.
3. Chuyển đổi câu hỏi thành Vector (Embedding)
4. Tìm kiếm ngữ cảnh trong Hybrid VectorDB (ChromaDB + BM25)
5. Sắp xếp lại mức độ liên quan (Rerank)
6. Sinh câu trả lời dựa trên LLM (Groq / Gemini)

## Kiến trúc
Module này tuân thủ chuẩn Dependency Injection của hệ thống tổng.
Nó đóng vai trò là Orchestrator, gọi tới các **Services** thực thi độc lập thay vì tự xử lý logic phần cứng trực tiếp.

## Cách sử dụng

Dưới đây là ví dụ cách các Agent trong LangGraph hoặc các Handler gọi module này:

```python
from src.modules.rag_module.schemas import RAGQuery, RAGResult
from src.modules.rag_module.main import RAGModuleImpl

from src.services.embedding_service import EmbeddingService
from src.services.retriever_service import RetrieverService
from src.services.reranker_service import RerankerService
from src.services.llm_service import LLMService

# 1. Khởi tạo các services (Thông thường Dependency Container (như FastAPI Depends) sẽ làm việc này)
embedding_svc = EmbeddingService()
retriever_svc = RetrieverService(chroma_host="localhost", chroma_port=8000)
reranker_svc = RerankerService()
llm_svc = LLMService(model_key="groq-llama3-70b")

# Mở kết nối đến DB
retriever_svc.connect()

# 2. Inject Services vào RAG Module
rag_module = RAGModuleImpl(
    embedding_service=embedding_svc,
    retriever_service=retriever_svc,
    reranker_service=reranker_svc,
    llm_service=llm_svc
)

# 3. Tạo Request và gọi
request = RAGQuery(
    question="Ngành Trí tuệ nhân tạo học những môn gì?",
    language="vi",    # hỗ trợ "auto", "vi", "en"
    retrieve_k=10,    # Số tài liệu lôi lên sơ bộ (FAISS + BM25)
    rerank_k=5        # Số tài liệu chắt lọc gửi cho LLM
)

if rag_module.health_check():
    result: RAGResult = rag_module.query(request)
    
    print("Câu trả lời:", result.answer)
    print("Thời gian xử lý:", result.latency_ms, "ms")
    print("Nguồn:", [s.title for s in result.sources])
```

## Giải thích về Input / Output Schema

### `RAGQuery` (Nguồn cấp dữ liệu vào)
Thuộc tính `language` có thể cài "auto" để tự phát hiện, hoặc ép buộc ngôn ngữ "en" / "vi" nếu đã biết trước từ Router.

### `RAGResult` (Nguồn xuất Dữ liệu ra)
Kết quả trả về được định dạng bằng `@dataclass(slots=True)`. Có thể dễ dàng dùng hàm `dataclasses.asdict(result)` để chuyển RAGResult thành JSON Python Dictionary truyền cho API Fastapi.
Các trường dữ liệu đầy đủ bao gồm: `question`, `answer`, `sources` (list của `SourceInfo`), `language`, `latency_ms`, `tokens_generated`, và `tokens_per_second`.
