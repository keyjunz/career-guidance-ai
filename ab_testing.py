"""
A/B Testing Script — So sánh các cấu hình model khác nhau.
Chạy thử nghiệm A/B giữa các model embedding, reranker, LLM.
"""

import json
import time
import gc
import argparse
import numpy as np
from pathlib import Path
from typing import Dict, List

import torch

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    DEVICE, RESULTS_DIR, DATA_DIR,
    EMBEDDING_MODELS, RERANKER_MODELS, LLM_MODELS,
    DEFAULT_EMBEDDING, DEFAULT_RERANKER, DEFAULT_LLM,
)
from evaluate import compute_bleu, compute_rouge_l, compute_f1, detect_hallucination


# ── Test Configurations ───────────────────────────────────────────
AB_CONFIGS = {
    # A/B test embedding models
    "embedding_comparison": {
        "description": "So sánh embedding models: multilingual-e5-small vs all-MiniLM-L6-v2",
        "variants": [
            {"name": "multilingual-e5-small", "embedding": "multilingual-e5-small", "reranker": DEFAULT_RERANKER},
            {"name": "all-MiniLM-L6-v2", "embedding": "all-MiniLM-L6-v2", "reranker": DEFAULT_RERANKER},
        ],
    },
    # A/B test reranker models
    "reranker_comparison": {
        "description": "So sánh reranker models: ms-marco-MiniLM vs bge-reranker-base",
        "variants": [
            {"name": "ms-marco-MiniLM", "embedding": DEFAULT_EMBEDDING, "reranker": "ms-marco-MiniLM-L6"},
            {"name": "bge-reranker-base", "embedding": DEFAULT_EMBEDDING, "reranker": "bge-reranker-base"},
        ],
    },
    # A/B test retrieval methods
    "retrieval_method": {
        "description": "So sánh retrieval methods: hybrid vs dense-only vs bm25-only",
        "variants": [
            {"name": "hybrid_rrf", "method": "hybrid"},
            {"name": "dense_only", "method": "dense"},
            {"name": "bm25_only", "method": "bm25"},
        ],
    },
}


def load_test_questions(qa_file: str = None, max_questions: int = 10) -> List[Dict]:
    """Load test questions cho A/B testing."""
    if qa_file is None:
        qa_file = str(DATA_DIR / "qa_test.json")

    qa_path = Path(qa_file)
    if not qa_path.exists():
        from evaluate import create_sample_qa_dataset
        qa_data = create_sample_qa_dataset(str(qa_path))
    else:
        with open(qa_path, "r", encoding="utf-8") as f:
            qa_data = json.load(f)

    return qa_data[:max_questions]


def ab_test_embedding(
    qa_data: List[Dict],
    variants: List[Dict],
    verbose: bool = True,
) -> Dict:
    """A/B test giữa các embedding models (không cần LLM)."""
    from models.embedding import EmbeddingModel
    from models.retriever import HybridRetriever
    from models.reranker import Reranker

    results = {}

    for variant in variants:
        name = variant["name"]
        print(f"\n{'─' * 50}")
        print(f"  Testing variant: {name}")
        print(f"{'─' * 50}")

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Load components
        emb = EmbeddingModel(model_key=variant["embedding"], device=DEVICE)
        reranker = Reranker(model_key=variant["reranker"], device=DEVICE)

        # Try to load existing retriever index
        retriever = HybridRetriever(dim=emb.dim)
        try:
            retriever.load(prefix="retriever")
            has_index = True
        except FileNotFoundError:
            has_index = False
            print(f"[Warning] No index found. Skipping retrieval test for {name}.")

        latencies = []
        scores = {"bleu": [], "rouge_l": [], "f1": []}

        for qa in qa_data:
            t0 = time.perf_counter()

            # Embed query
            query_emb = emb.encode_query(qa["question"])

            if has_index:
                # Retrieve
                retrieved = retriever.search(qa["question"], query_emb, top_k=10)
                # Rerank
                reranked = reranker.rerank(qa["question"], retrieved, top_k=5)
                context = " ".join([d["text"] for d in reranked])
            else:
                context = ""

            latency = (time.perf_counter() - t0) * 1000
            latencies.append(latency)

            # Compute metrics against retrieved context as proxy
            if context and qa.get("reference_answer"):
                scores["bleu"].append(compute_bleu(qa["reference_answer"], context))
                scores["rouge_l"].append(compute_rouge_l(qa["reference_answer"], context))
                scores["f1"].append(compute_f1(qa["reference_answer"], context))

        results[name] = {
            "embedding_model": variant["embedding"],
            "reranker_model": variant["reranker"],
            "avg_latency_ms": round(np.mean(latencies), 2),
            "p95_latency_ms": round(np.percentile(latencies, 95), 2),
            "avg_bleu": round(np.mean(scores["bleu"]), 2) if scores["bleu"] else None,
            "avg_rouge_l": round(np.mean(scores["rouge_l"]), 2) if scores["rouge_l"] else None,
            "avg_f1": round(np.mean(scores["f1"]), 2) if scores["f1"] else None,
            "n_questions": len(qa_data),
        }

        if verbose:
            r = results[name]
            print(f"\n  Results for {name}:")
            print(f"    Avg latency: {r['avg_latency_ms']:.1f}ms")
            print(f"    P95 latency: {r['p95_latency_ms']:.1f}ms")
            if r["avg_bleu"] is not None:
                print(f"    Avg BLEU:    {r['avg_bleu']:.1f}")
                print(f"    Avg ROUGE-L: {r['avg_rouge_l']:.1f}")
                print(f"    Avg F1:      {r['avg_f1']:.1f}")

        # Cleanup
        del emb, reranker, retriever
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    return results


def ab_test_retrieval_method(
    qa_data: List[Dict],
    verbose: bool = True,
) -> Dict:
    """A/B test giữa các phương pháp retrieval: hybrid, dense, bm25."""
    from models.embedding import EmbeddingModel
    from models.retriever import HybridRetriever

    emb = EmbeddingModel(device=DEVICE)
    retriever = HybridRetriever(dim=emb.dim)

    try:
        retriever.load(prefix="retriever")
    except FileNotFoundError:
        print("[Error] No index found. Run build_vectordb.py first.")
        return {}

    methods = {
        "hybrid_rrf": lambda q, qe: retriever.search(q, qe, top_k=10, method="rrf"),
        "hybrid_weighted": lambda q, qe: retriever.search(q, qe, top_k=10, method="weighted"),
        "dense_only": lambda q, qe: retriever.dense_only_search(qe, k=10),
        "bm25_only": lambda q, qe: retriever.bm25_only_search(q, k=10),
    }

    results = {}
    for method_name, search_fn in methods.items():
        print(f"\n  Testing: {method_name}")
        latencies = []
        retrieval_scores = []

        for qa in qa_data:
            query_emb = emb.encode_query(qa["question"])

            t0 = time.perf_counter()
            retrieved = search_fn(qa["question"], query_emb)
            latency = (time.perf_counter() - t0) * 1000
            latencies.append(latency)

            # Check if reference answer terms appear in retrieved docs
            if retrieved and qa.get("reference_answer"):
                context = " ".join([d["text"] for d in retrieved])
                f1 = compute_f1(qa["reference_answer"], context)
                retrieval_scores.append(f1)

        results[method_name] = {
            "avg_latency_ms": round(np.mean(latencies), 2),
            "p95_latency_ms": round(np.percentile(latencies, 95), 2),
            "avg_retrieval_f1": round(np.mean(retrieval_scores), 2) if retrieval_scores else None,
            "n_questions": len(qa_data),
        }

        if verbose:
            r = results[method_name]
            print(f"    Avg latency:       {r['avg_latency_ms']:.2f}ms")
            print(f"    Avg retrieval F1:  {r['avg_retrieval_f1']}")

    return results


def run_ab_tests(
    test_name: str = "all",
    max_questions: int = 10,
    output_file: str = None,
):
    """Chạy A/B tests."""
    if output_file is None:
        output_file = str(RESULTS_DIR / "ab_test_results.json")

    print("=" * 60)
    print("  A/B TESTING SUITE")
    print("=" * 60)

    qa_data = load_test_questions(max_questions=max_questions)
    print(f"  Test questions: {len(qa_data)}")

    all_results = {}

    # Test 1: Embedding comparison
    if test_name in ("all", "embedding"):
        print(f"\n{'═' * 50}")
        print(f"  TEST: Embedding Model Comparison")
        print(f"{'═' * 50}")
        all_results["embedding_comparison"] = ab_test_embedding(
            qa_data,
            AB_CONFIGS["embedding_comparison"]["variants"],
        )

    # Test 2: Retrieval method comparison
    if test_name in ("all", "retrieval"):
        print(f"\n{'═' * 50}")
        print(f"  TEST: Retrieval Method Comparison")
        print(f"{'═' * 50}")
        all_results["retrieval_method"] = ab_test_retrieval_method(qa_data)

    # Test 3: Reranker comparison
    if test_name in ("all", "reranker"):
        print(f"\n{'═' * 50}")
        print(f"  TEST: Reranker Model Comparison")
        print(f"{'═' * 50}")
        all_results["reranker_comparison"] = ab_test_embedding(
            qa_data,
            AB_CONFIGS["reranker_comparison"]["variants"],
        )

    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"  A/B TEST SUMMARY")
    print(f"{'=' * 60}")

    for test_name, test_results in all_results.items():
        print(f"\n  {test_name}:")
        if isinstance(test_results, dict):
            for variant_name, metrics in test_results.items():
                if isinstance(metrics, dict):
                    lat = metrics.get("avg_latency_ms", "N/A")
                    f1 = metrics.get("avg_f1") or metrics.get("avg_retrieval_f1") or "N/A"
                    print(f"    {variant_name:25s}: latency={lat}ms, quality={f1}")

    print(f"\n  Results saved to: {output_file}")
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A/B Testing for RAG Pipeline")
    parser.add_argument("--test", type=str, default="all",
                       choices=["all", "embedding", "retrieval", "reranker"])
    parser.add_argument("--max-questions", type=int, default=10)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run_ab_tests(
        test_name=args.test,
        max_questions=args.max_questions,
        output_file=args.output,
    )
