"""
RAG Pipeline — End-to-end Retrieval-Augmented Generation pipeline.
Kết hợp: Embedding → Hybrid Retriever → Reranker → LLM Generator
"""

import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    DEVICE, DEFAULT_EMBEDDING, DEFAULT_RERANKER, DEFAULT_LLM,
    RETRIEVER_FINAL_K, RERANKER_TOP_K,
    INDEX_DIR, RESULTS_DIR,
    USE_API_LLM, DEFAULT_API_LLM,
)
from models.embedding import EmbeddingModel
from models.retriever import HybridRetriever
from models.reranker import Reranker
from models.llm_generator import LLMGenerator, APILLMGenerator


class RAGPipeline:
    """
    End-to-end RAG pipeline:
    Query → Embedding → Retrieve (Hybrid BM25+Dense) → Rerank → LLM Generate
    """

    def __init__(
        self,
        embedding_key: str = DEFAULT_EMBEDDING,
        reranker_key: str = DEFAULT_RERANKER,
        llm_key: str = DEFAULT_LLM,
        api_llm_key: str = DEFAULT_API_LLM,
        device: str = DEVICE,
        load_llm: bool = True,
        use_api_llm: bool = USE_API_LLM,
    ):
        self.device = device
        self.timings = {}

        # 1. Embedding model
        print("=" * 60)
        print("  INITIALIZING RAG PIPELINE")
        print("=" * 60)

        t0 = time.perf_counter()
        self.embedding = EmbeddingModel(model_key=embedding_key, device=device)
        self.timings["load_embedding"] = (time.perf_counter() - t0) * 1000

        # 2. Retriever (load saved index)
        t0 = time.perf_counter()
        self.retriever = HybridRetriever(dim=self.embedding.dim)
        try:
            self.retriever.load(prefix="retriever")
        except FileNotFoundError:
            print("[Warning] No saved index found. Run build_vectordb.py first.")
        self.timings["load_retriever"] = (time.perf_counter() - t0) * 1000

        # 3. Reranker
        t0 = time.perf_counter()
        self.reranker = Reranker(model_key=reranker_key, device=device)
        self.timings["load_reranker"] = (time.perf_counter() - t0) * 1000

        # 4. LLM Generator (API hoặc Local)
        if load_llm:
            t0 = time.perf_counter()
            if use_api_llm:
                self.llm = APILLMGenerator(model_key=api_llm_key)
                self.llm.load()
                print(f"[Pipeline] Using API LLM: {self.llm.model_name}")
            else:
                self.llm = LLMGenerator(model_key=llm_key, device=device)
                self.llm.load()
            self.timings["load_llm"] = (time.perf_counter() - t0) * 1000
        else:
            self.llm = None

        total_load = sum(self.timings.values())
        print(f"\n[Pipeline] All components loaded in {total_load / 1000:.1f}s")
        for k, v in self.timings.items():
            print(f"  {k}: {v:.0f}ms")

    def query(
        self,
        question: str,
        language: str = "en",
        retrieve_k: int = RETRIEVER_FINAL_K,
        rerank_k: int = RERANKER_TOP_K,
        verbose: bool = True,
    ) -> Dict:
        """
        Chạy full RAG pipeline cho một câu hỏi.

        Args:
            question: Câu hỏi người dùng
            language: 'en' hoặc 'vi'
            retrieve_k: Số docs trước rerank
            rerank_k: Số docs sau rerank (đưa vào LLM)
            verbose: In chi tiết

        Returns:
            Dict: answer, sources, latency breakdown, etc.
        """
        pipeline_start = time.perf_counter()
        step_times = {}

        # Step 1: Embed query
        t0 = time.perf_counter()
        query_embedding = self.embedding.encode_query(question)
        step_times["embedding"] = (time.perf_counter() - t0) * 1000

        # Step 2: Hybrid Retrieve
        t0 = time.perf_counter()
        retrieved = self.retriever.search(
            query=question,
            query_embedding=query_embedding,
            top_k=retrieve_k,
        )
        step_times["retrieval"] = (time.perf_counter() - t0) * 1000

        # Step 3: Rerank
        t0 = time.perf_counter()
        reranked = self.reranker.rerank(
            query=question,
            documents=retrieved,
            top_k=rerank_k,
        )
        step_times["reranking"] = (time.perf_counter() - t0) * 1000

        # Step 4: Build context
        context_parts = []
        sources = []
        for i, doc in enumerate(reranked):
            context_parts.append(f"[{i+1}] {doc['text']}")
            sources.append({
                "rank": i + 1,
                "text": doc["text"][:100] + "...",
                "source": doc.get("source", "unknown"),
                "title": doc.get("title", ""),
                "rerank_score": doc.get("rerank_score", 0),
            })
        context = "\n\n".join(context_parts)

        # Step 5: LLM Generate
        if self.llm is not None:
            t0 = time.perf_counter()
            llm_result = self.llm.generate(
                question=question,
                context=context,
                language=language,
            )
            step_times["generation"] = (time.perf_counter() - t0) * 1000
            answer = llm_result["answer"]
            tokens_generated = llm_result["tokens_generated"]
            tokens_per_second = llm_result["tokens_per_second"]
        else:
            answer = f"[LLM not loaded] Context retrieved:\n{context}"
            tokens_generated = 0
            tokens_per_second = 0
            step_times["generation"] = 0

        total_time = (time.perf_counter() - pipeline_start) * 1000

        result = {
            "question": question,
            "answer": answer,
            "sources": sources,
            "context": context,
            "language": language,
            "latency": {
                "total_ms": total_time,
                **{f"{k}_ms": v for k, v in step_times.items()},
            },
            "tokens_generated": tokens_generated,
            "tokens_per_second": tokens_per_second,
        }

        if verbose:
            print(f"\n{'─' * 60}")
            print(f"Question: {question}")
            print(f"{'─' * 60}")
            print(f"\nAnswer:\n{answer}")
            print(f"\n{'─' * 60}")
            print(f"Latency breakdown:")
            for k, v in step_times.items():
                bar_len = int(v / total_time * 30) if total_time > 0 else 0
                bar = "█" * bar_len
                print(f"  {k:12s}: {v:8.1f}ms  {bar}")
            print(f"  {'TOTAL':12s}: {total_time:8.1f}ms")
            print(f"\nSources ({len(sources)}):")
            for s in sources:
                print(f"  [{s['rank']}] ({s['source']}) {s['title']}: {s['text'][:60]}...")

        return result

    def batch_query(
        self,
        questions: List[str],
        language: str = "en",
        verbose: bool = False,
    ) -> List[Dict]:
        """Xử lý batch câu hỏi."""
        results = []
        for i, q in enumerate(questions):
            print(f"\n[{i+1}/{len(questions)}] Processing: {q[:50]}...")
            result = self.query(q, language=language, verbose=verbose)
            results.append(result)
        return results

    def interactive(self):
        """Chế độ interactive chat."""
        print("\n" + "=" * 60)
        print("  RAG CHATBOT — Interactive Mode")
        print("  Type 'quit' to exit, 'vi' to switch to Vietnamese")
        print("=" * 60)

        language = "en"
        while True:
            try:
                question = input(f"\n[{language.upper()}] You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                break
            if question.lower() == "vi":
                language = "vi"
                print("Switched to Vietnamese mode.")
                continue
            if question.lower() == "en":
                language = "en"
                print("Switched to English mode.")
                continue

            self.query(question, language=language, verbose=True)


def main():
    parser = argparse.ArgumentParser(description="RAG Chatbot Pipeline")
    parser.add_argument("--query", type=str, default=None, help="Single query")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--embedding", type=str, default=DEFAULT_EMBEDDING)
    parser.add_argument("--reranker", type=str, default=DEFAULT_RERANKER)
    parser.add_argument("--llm", type=str, default=DEFAULT_LLM)
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM loading")
    parser.add_argument("--use-api", action="store_true", default=USE_API_LLM,
                       help="Use API LLM (Groq/Gemini) instead of local")
    parser.add_argument("--use-local", action="store_true", help="Force local LLM")
    parser.add_argument("--api-model", type=str, default=DEFAULT_API_LLM,
                       help="API model key (e.g. groq-llama3-70b)")
    parser.add_argument("--language", type=str, default="en", choices=["en", "vi"])
    parser.add_argument("--device", type=str, default=DEVICE)
    args = parser.parse_args()

    # Determine LLM mode
    use_api = args.use_api and not args.use_local

    rag = RAGPipeline(
        embedding_key=args.embedding,
        reranker_key=args.reranker,
        llm_key=args.llm,
        api_llm_key=args.api_model,
        device=args.device,
        load_llm=not args.no_llm,
        use_api_llm=use_api,
    )

    if args.query:
        rag.query(args.query, language=args.language, verbose=True)
    elif args.interactive:
        rag.interactive()
    else:
        # Demo query
        demo_questions = [
            "What is the transformer architecture and how does self-attention work?",
            "Explain the difference between supervised and unsupervised learning.",
            "How does backpropagation algorithm work in neural networks?",
        ]
        for q in demo_questions:
            rag.query(q, verbose=True)
            print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
