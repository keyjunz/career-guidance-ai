"""
Benchmark — Đo latency, throughput, memory cho từng component RAG.
"""

import gc
import time
import json
import argparse
import numpy as np
from pathlib import Path

import torch
import psutil

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    DEVICE, RESULTS_DIR,
    DEFAULT_EMBEDDING, DEFAULT_RERANKER, DEFAULT_LLM,
    EMBEDDING_MODELS, RERANKER_MODELS, LLM_MODELS,
)


def get_memory_stats():
    """Lấy thông tin memory hiện tại."""
    ram = psutil.virtual_memory()
    stats = {
        "ram_used_gb": round(ram.used / 1024**3, 2),
        "ram_total_gb": round(ram.total / 1024**3, 2),
        "ram_percent": ram.percent,
    }
    if torch.cuda.is_available():
        stats["vram_allocated_mb"] = round(torch.cuda.memory_allocated() / 1024**2, 1)
        stats["vram_reserved_mb"] = round(torch.cuda.memory_reserved() / 1024**2, 1)
        stats["vram_total_mb"] = round(torch.cuda.get_device_properties(0).total_mem / 1024**2, 1)
    return stats


def benchmark_embedding(model_keys: list = None, n_runs: int = 50):
    """Benchmark tất cả embedding models."""
    from models.embedding import EmbeddingModel

    if model_keys is None:
        model_keys = list(EMBEDDING_MODELS.keys())

    results = {}
    test_query = "What is the transformer architecture in deep learning?"
    test_passages = [
        "The Transformer is a model architecture introduced in Attention Is All You Need.",
        "Convolutional neural networks use filters to process image data efficiently.",
        "Recurrent neural networks process sequential data using hidden state memory.",
    ] * 10  # 30 passages for batch test

    for key in model_keys:
        print(f"\n[Benchmark Embedding] {key}")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        mem_before = get_memory_stats()
        model = EmbeddingModel(model_key=key, device=DEVICE)
        mem_after = get_memory_stats()

        # Single query latency
        latency_result = model.benchmark_latency(test_query, n_runs=n_runs)

        # Batch throughput
        start = time.perf_counter()
        model.encode_passages(test_passages, show_progress=False)
        batch_time = (time.perf_counter() - start) * 1000
        throughput = len(test_passages) / (batch_time / 1000)

        results[key] = {
            "model_name": EMBEDDING_MODELS[key]["name"],
            "dim": EMBEDDING_MODELS[key]["dim"],
            "latency_avg_ms": round(latency_result["avg"], 2),
            "latency_p95_ms": round(latency_result["p95"], 2),
            "batch_30_ms": round(batch_time, 2),
            "throughput_docs_per_sec": round(throughput, 1),
            "model_memory_mb": round(model.get_memory_usage_mb(), 1),
            "ram_delta_gb": round(
                mem_after["ram_used_gb"] - mem_before["ram_used_gb"], 2
            ),
        }

        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return results


def benchmark_reranker(model_keys: list = None, n_runs: int = 30):
    """Benchmark tất cả reranker models."""
    from models.reranker import Reranker

    if model_keys is None:
        model_keys = list(RERANKER_MODELS.keys())

    results = {}
    test_query = "How does attention mechanism work?"
    test_passages = [
        "Attention mechanisms allow models to focus on relevant parts of input.",
        "CNNs use convolutional filters to extract spatial features.",
        "Transformers use self-attention instead of recurrence.",
        "BERT is pre-trained with masked language modeling.",
        "GPT generates text in autoregressive fashion.",
        "Neural networks learn through backpropagation.",
        "Dropout prevents overfitting by randomly disabling neurons.",
        "Batch normalization stabilizes training dynamics.",
        "Learning rate scheduling improves convergence.",
        "Gradient clipping prevents exploding gradients.",
    ]
    docs = [{"text": p, "source": "test", "chunk_id": i} for i, p in enumerate(test_passages)]

    for key in model_keys:
        print(f"\n[Benchmark Reranker] {key}")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        mem_before = get_memory_stats()
        reranker = Reranker(model_key=key, device=DEVICE)
        mem_after = get_memory_stats()

        latency_result = reranker.benchmark_latency(
            query=test_query,
            passages=test_passages,
            n_runs=n_runs,
        )

        results[key] = {
            "model_name": RERANKER_MODELS[key]["name"],
            "latency_avg_ms": round(latency_result["avg"], 2),
            "latency_p95_ms": round(latency_result["p95"], 2),
            "k": len(test_passages),
            "model_memory_mb": round(reranker.get_memory_usage_mb(), 1),
            "ram_delta_gb": round(
                mem_after["ram_used_gb"] - mem_before["ram_used_gb"], 2
            ),
        }

        del reranker
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return results


def benchmark_llm(model_keys: list = None, n_runs: int = 3):
    """Benchmark LLM models."""
    from models.llm_generator import LLMGenerator

    if model_keys is None:
        model_keys = [DEFAULT_LLM]  # Chỉ benchmark default do VRAM hạn chế

    results = {}
    test_context = (
        "The Transformer is a deep learning architecture introduced by Vaswani et al. "
        "It uses self-attention mechanisms instead of recurrence. Key components include "
        "multi-head attention, positional encoding, and feed-forward layers."
    )
    test_question = "What are the key components of the Transformer?"

    for key in model_keys:
        print(f"\n[Benchmark LLM] {key}")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        mem_before = get_memory_stats()
        llm = LLMGenerator(model_key=key, device=DEVICE)
        llm.load()
        mem_after = get_memory_stats()

        bench = llm.benchmark_latency(n_runs=n_runs)

        results[key] = {
            "model_name": LLM_MODELS[key]["name"],
            "quantization": LLM_MODELS[key]["quantization"],
            "avg_latency_ms": round(bench["avg_latency_ms"], 0),
            "avg_tokens_per_sec": round(bench["avg_tokens_per_second"], 1),
            "vram_mb": round(
                mem_after.get("vram_allocated_mb", 0) - mem_before.get("vram_allocated_mb", 0), 1
            ),
            "ram_delta_gb": round(
                mem_after["ram_used_gb"] - mem_before["ram_used_gb"], 2
            ),
        }

        llm.unload()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return results


def benchmark_retriever(n_docs: int = 5000, n_runs: int = 100):
    """Benchmark retriever với synthetic docs."""
    from models.retriever import HybridRetriever

    print(f"\n[Benchmark Retriever] {n_docs} documents")
    dim = EMBEDDING_MODELS[DEFAULT_EMBEDDING]["dim"]

    # Synthetic data
    np.random.seed(42)
    docs = [
        {"text": f"Document {i} about artificial intelligence and deep learning topic {i % 50}.",
         "source": "synthetic", "chunk_id": i}
        for i in range(n_docs)
    ]
    embeddings = np.random.randn(n_docs, dim).astype(np.float32)
    query_emb = np.random.randn(dim).astype(np.float32)
    query_text = "artificial intelligence deep learning"

    retriever = HybridRetriever(dim=dim)
    retriever.build_index(docs, embeddings)

    latency_data = retriever.benchmark_latency(query_text, query_emb, n_runs=n_runs)

    results = {
        "n_docs": n_docs,
        "dim": dim,
    }
    for method, lats in latency_data.items():
        results[f"{method}_avg_ms"] = round(np.mean(lats), 2)
        results[f"{method}_p95_ms"] = round(np.percentile(lats, 95), 2)

    return results


def run_full_benchmark(output_file: str = None):
    """Chạy benchmark toàn bộ pipeline."""
    if output_file is None:
        output_file = str(RESULTS_DIR / "benchmark_results.json")

    print("=" * 60)
    print("  FULL BENCHMARK SUITE")
    print("=" * 60)
    print(f"  Device: {DEVICE}")
    mem = get_memory_stats()
    print(f"  RAM: {mem['ram_used_gb']}/{mem['ram_total_gb']} GB")
    if torch.cuda.is_available():
        print(f"  VRAM: {mem['vram_allocated_mb']}/{mem['vram_total_mb']} MB")

    all_results = {
        "device": DEVICE,
        "system": get_memory_stats(),
    }

    # 1. Embedding benchmark
    try:
        print("\n" + "─" * 40)
        print("  EMBEDDING MODELS")
        print("─" * 40)
        all_results["embedding"] = benchmark_embedding(
            model_keys=[DEFAULT_EMBEDDING],
            n_runs=50,
        )
    except Exception as e:
        print(f"[Error] Embedding benchmark: {e}")
        all_results["embedding"] = {"error": str(e)}

    # 2. Retriever benchmark
    try:
        print("\n" + "─" * 40)
        print("  RETRIEVER")
        print("─" * 40)
        all_results["retriever"] = benchmark_retriever(n_docs=5000)
    except Exception as e:
        print(f"[Error] Retriever benchmark: {e}")
        all_results["retriever"] = {"error": str(e)}

    # 3. Reranker benchmark
    try:
        print("\n" + "─" * 40)
        print("  RERANKER MODELS")
        print("─" * 40)
        all_results["reranker"] = benchmark_reranker(
            model_keys=[DEFAULT_RERANKER],
            n_runs=30,
        )
    except Exception as e:
        print(f"[Error] Reranker benchmark: {e}")
        all_results["reranker"] = {"error": str(e)}

    # 4. LLM benchmark
    try:
        print("\n" + "─" * 40)
        print("  LLM MODELS")
        print("─" * 40)
        all_results["llm"] = benchmark_llm(
            model_keys=[DEFAULT_LLM],
            n_runs=3,
        )
    except Exception as e:
        print(f"[Error] LLM benchmark: {e}")
        all_results["llm"] = {"error": str(e)}

    # Save
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  BENCHMARK COMPLETE")
    print(f"  Results saved to: {output_file}")
    print(f"{'=' * 60}")

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Component Benchmark")
    parser.add_argument("--component", type=str, default="all",
                       choices=["all", "embedding", "retriever", "reranker", "llm"])
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    if args.component == "all":
        run_full_benchmark(args.output)
    elif args.component == "embedding":
        results = benchmark_embedding()
        print(json.dumps(results, indent=2))
    elif args.component == "retriever":
        results = benchmark_retriever()
        print(json.dumps(results, indent=2))
    elif args.component == "reranker":
        results = benchmark_reranker()
        print(json.dumps(results, indent=2))
    elif args.component == "llm":
        results = benchmark_llm()
        print(json.dumps(results, indent=2))
