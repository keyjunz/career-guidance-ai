from pathlib import Path

import torch

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
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CACHE_DIR = Path(__file__).parent.parent.parent / "_cache"
CACHE_DIR.mkdir(exist_ok=True)
