"""
Cấu hình tập trung cho RAG Chatbot pipeline.
Tất cả hyperparameters, model paths, và thresholds được định nghĩa ở đây.
"""

import os
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # Load .env file nếu có

# ─── Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
RESULTS_DIR = BASE_DIR / "results"
INDEX_DIR = BASE_DIR / "indexes"

for d in [DATA_DIR, CACHE_DIR, RESULTS_DIR, INDEX_DIR]:
    d.mkdir(exist_ok=True)

# ─── Device ──────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
VRAM_GB = (
    torch.cuda.get_device_properties(0).total_mem / 1024**3
    if torch.cuda.is_available()
    else 0
)

# ─── Embedding ───────────────────────────────────────────────────────
EMBEDDING_MODELS = {
    "multilingual-e5-small": {
        "name": "intfloat/multilingual-e5-small",
        "dim": 384,
        "max_seq_length": 512,
        "prefix_query": "query: ",
        "prefix_passage": "passage: ",
    },
    "all-MiniLM-L6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "dim": 384,
        "max_seq_length": 256,
        "prefix_query": "",
        "prefix_passage": "",
    },
    "bge-m3": {
        "name": "BAAI/bge-m3",
        "dim": 1024,
        "max_seq_length": 8192,
        "prefix_query": "",
        "prefix_passage": "",
    },
}
DEFAULT_EMBEDDING = "multilingual-e5-small"

# ─── Retriever ───────────────────────────────────────────────────────
RETRIEVER_TOP_K = 20          # Số kết quả từ mỗi retriever trước khi fusion
RETRIEVER_FINAL_K = 10        # Số kết quả sau RRF fusion đưa vào reranker
BM25_K1 = 1.5
BM25_B = 0.75
RRF_K = 60                    # Constant trong Reciprocal Rank Fusion

# ─── Reranker ────────────────────────────────────────────────────────
RERANKER_MODELS = {
    "ms-marco-MiniLM-L6": {
        "name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "max_length": 512,
    },
    "bge-reranker-base": {
        "name": "BAAI/bge-reranker-base",
        "max_length": 512,
    },
    "monoT5-base": {
        "name": "castorini/monoT5-base-msmarco-10k",
        "max_length": 512,
    },
}
DEFAULT_RERANKER = "ms-marco-MiniLM-L6"
RERANKER_TOP_K = 5            # Số kết quả cuối cùng sau rerank

# ─── LLM ─────────────────────────────────────────────────────────────
LLM_MODELS = {
    "qwen2.5-1.5b": {
        "name": "Qwen/Qwen2.5-1.5B-Instruct",
        "type": "transformers",
        "max_new_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.9,
        "quantization": "none",          # float16 thẳng lên GPU, tránh paging file issue
    },
    "qwen2.5-3b": {
        "name": "Qwen/Qwen2.5-3B-Instruct",
        "type": "transformers",
        "max_new_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.9,
        "quantization": "4bit",
    },
    "gemma-2-2b": {
        "name": "google/gemma-2-2b-it",
        "type": "transformers",
        "max_new_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.9,
        "quantization": "none",
    },
    "phi-3-mini": {
        "name": "microsoft/Phi-3-mini-4k-instruct",
        "type": "transformers",
        "max_new_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.9,
        "quantization": "none",
    },
}
DEFAULT_LLM = "qwen2.5-1.5b"

# ─── API LLM (Groq / Gemini) ────────────────────────────────────────
# Dùng API thay vì self-host LLM → không cần GPU, nhanh, mạnh hơn
USE_API_LLM = True  # True = dùng API, False = dùng local transformers

API_LLM_MODELS = {
    "groq-llama3-70b": {
        "provider": "groq",
        "name": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
    "groq-llama3-8b": {
        "provider": "groq",
        "name": "llama-3.1-8b-instant",
        "api_key_env": "GROQ_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
    "groq-gemma2-9b": {
        "provider": "groq",
        "name": "gemma2-9b-it",
        "api_key_env": "GROQ_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
    "gemini-flash": {
        "provider": "gemini",
        "name": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "max_tokens": 1024,
        "temperature": 0.3,
    },
}
DEFAULT_API_LLM = "groq-llama3-70b"

# API Keys (đọc từ environment variable hoặc .env file)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Data / Chunking ────────────────────────────────────────────────
CHUNK_SIZE = 512               # tokens per chunk
CHUNK_OVERLAP = 50             # token overlap giữa các chunk
TARGET_DOC_COUNT = 7000        # Số đoạn mục tiêu (5K-10K)

# Wikipedia categories để crawl
WIKI_CATEGORIES = [
    "Artificial intelligence",
    "Machine learning",
    "Deep learning",
    "Natural language processing",
    "Computer vision",
    "Neural networks",
    "Reinforcement learning",
    "Data science",
    "Algorithms",
    "Computer science",
    "Information retrieval",
    "Transformer (machine learning model)",
    "Convolutional neural network",
    "Recurrent neural network",
    "Generative adversarial network",
]

# ─── Evaluation ──────────────────────────────────────────────────────
EVAL_METRICS = ["bleu", "rouge_l", "f1", "latency", "throughput", "memory"]
BLEU_THRESHOLD = 25
ROUGE_L_THRESHOLD = 40
HALLUCINATION_THRESHOLD = 0.05  # 5%
MAX_ANSWER_WORDS = 500

# ─── RAG Prompt Template ────────────────────────────────────────────
RAG_PROMPT_TEMPLATE = """You are an expert AI/Computer Science assistant. Answer the question using ONLY the provided context. If the context doesn't contain enough information, say so honestly. Keep your answer concise (under 500 words), accurate, and well-structured.

### Context:
{context}

### Question:
{question}

### Answer:"""

RAG_PROMPT_TEMPLATE_VI = """Bạn là trợ lý chuyên gia AI/Khoa học Máy tính. Trả lời câu hỏi CHỈ dựa trên ngữ cảnh được cung cấp. Nếu ngữ cảnh không chứa đủ thông tin, hãy nói rõ điều đó. Giữ câu trả lời ngắn gọn (dưới 500 từ), chính xác và có cấu trúc rõ ràng.

### Ngữ cảnh:
{context}

### Câu hỏi:
{question}

### Trả lời:"""


def print_config():
    """In thông tin cấu hình hệ thống."""
    print("=" * 60)
    print("  RAG CHATBOT CONFIGURATION")
    print("=" * 60)
    print(f"  Device:       {DEVICE}")
    print(f"  GPU:          {GPU_NAME}")
    print(f"  VRAM:         {VRAM_GB:.1f} GB")
    print(f"  Embedding:    {EMBEDDING_MODELS[DEFAULT_EMBEDDING]['name']}")
    print(f"  Reranker:     {RERANKER_MODELS[DEFAULT_RERANKER]['name']}")
    print(f"  LLM:          {LLM_MODELS[DEFAULT_LLM]['name']}")
    print(f"  Vector dim:   {EMBEDDING_MODELS[DEFAULT_EMBEDDING]['dim']}")
    print(f"  Chunk size:   {CHUNK_SIZE} tokens")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
