import torch

RERANKER_MODELS = {
    "ms-marco-MiniLM-L6": {"name": "cross-encoder/ms-marco-MiniLM-L-6-v2", "max_length": 512},
    "bge-reranker-base": {"name": "BAAI/bge-reranker-base", "max_length": 512},
    "monoT5-base": {"name": "castorini/monoT5-base-msmarco-10k", "max_length": 512},
}

DEFAULT_RERANKER = "ms-marco-MiniLM-L6"
RERANKER_TOP_K = 5
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
