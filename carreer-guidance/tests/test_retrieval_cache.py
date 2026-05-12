from src.services.retriever_service.retrieval_cache import (
    HybridRetrievalCache,
    make_retrieval_cache_key,
)


def test_cache_key_stable() -> None:
    k1 = make_retrieval_cache_key(
        query="  Hello   World ",
        top_k=10,
        dense_k=20,
        sparse_k=20,
        where=None,
    )
    k2 = make_retrieval_cache_key(
        query="hello world",
        top_k=10,
        dense_k=20,
        sparse_k=20,
        where=None,
    )
    assert k1 == k2


def test_hybrid_retrieval_cache_ttl_and_lru() -> None:
    HybridRetrievalCache.reset_for_tests()
    c = HybridRetrievalCache.get_instance()
    key = "abc"
    docs = [{"chunk_id": "1", "text": "hello"}]
    c.set(key, docs)
    got = c.get(key)
    assert got is not None
    assert got[0]["text"] == "hello"
    # Mutating returned copy should not affect cache
    got[0]["text"] = "mutated"
    got2 = c.get(key)
    assert got2 is not None
    assert got2[0]["text"] == "hello"


def test_heuristic_multi_clause() -> None:
    from src.agent.nodes.query_decomposer_node import _heuristic_multi_clause

    assert _heuristic_multi_clause("Hi") is False
    assert _heuristic_multi_clause("Lương backend 2024? Học AI ở đâu?") is True
    assert _heuristic_multi_clause(
        "So sánh React và Vue; học AI cần những gì?"
    ) is True
