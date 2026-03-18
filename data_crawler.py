"""
Data Crawler — Crawl AI/CS knowledge từ Wikipedia, arXiv abstracts, 
và tạo simulated Stack Exchange data.
Chunk thành đoạn 512 token, lưu JSON.
"""

import json
import re
import time
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, TARGET_DOC_COUNT, WIKI_CATEGORIES

try:
    import wikipediaapi
    HAS_WIKIPEDIA = True
except ImportError:
    HAS_WIKIPEDIA = False
    print("[Warning] wikipedia-api not installed. pip install wikipedia-api")

try:
    import arxiv
    HAS_ARXIV = True
except ImportError:
    HAS_ARXIV = False
    print("[Warning] arxiv not installed. pip install arxiv")

from transformers import AutoTokenizer


def get_tokenizer():
    """Load a fast tokenizer for chunking."""
    return AutoTokenizer.from_pretrained("bert-base-uncased", use_fast=True)


# ── Chunking ──────────────────────────────────────────────────────
def chunk_text(
    text: str,
    tokenizer,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Chunk text thành các đoạn chunk_size tokens với overlap.
    """
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
        chunk_text = chunk_text.strip()
        if len(chunk_text) > 50:  # Bỏ qua chunks quá ngắn
            chunks.append(chunk_text)
        start += chunk_size - overlap
    return chunks


# ── Wikipedia Crawler ──────────────────────────────────────────────
def crawl_wikipedia(
    categories: List[str] = WIKI_CATEGORIES,
    max_pages_per_category: int = 30,
    language: str = "en",
) -> List[Dict]:
    """Crawl Wikipedia articles từ các AI/CS categories."""
    if not HAS_WIKIPEDIA:
        print("[Wikipedia] Skipped — wikipedia-api not installed")
        return []

    wiki = wikipediaapi.Wikipedia(
        user_agent="RAG_Chatbot_Research/1.0",
        language=language,
    )

    articles = []
    seen_titles = set()

    for category_name in categories:
        print(f"[Wikipedia] Crawling category: {category_name}...")
        cat = wiki.page(f"Category:{category_name}")

        if not cat.exists():
            # Thử tìm trực tiếp bài viết
            page = wiki.page(category_name)
            if page.exists() and page.title not in seen_titles:
                seen_titles.add(page.title)
                articles.append({
                    "title": page.title,
                    "text": page.text,
                    "source": "wikipedia",
                    "url": page.fullurl if hasattr(page, "fullurl") else f"https://en.wikipedia.org/wiki/{page.title.replace(' ', '_')}",
                })
            continue

        count = 0
        for title, page in cat.categorymembers.items():
            if count >= max_pages_per_category:
                break
            if page.ns != wikipediaapi.Namespace.MAIN:
                continue
            if title in seen_titles:
                continue

            full_page = wiki.page(title)
            if full_page.exists() and len(full_page.text) > 200:
                seen_titles.add(title)
                articles.append({
                    "title": full_page.title,
                    "text": full_page.text,
                    "source": "wikipedia",
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                })
                count += 1
                time.sleep(0.2)  # Rate limiting

    print(f"[Wikipedia] Crawled {len(articles)} articles")
    return articles


# ── arXiv Crawler ─────────────────────────────────────────────────
def crawl_arxiv(
    queries: List[str] = None,
    max_results_per_query: int = 100,
) -> List[Dict]:
    """Crawl arXiv abstracts cho AI/CS papers."""
    if not HAS_ARXIV:
        print("[arXiv] Skipped — arxiv not installed")
        return []

    if queries is None:
        queries = [
            "transformer architecture deep learning",
            "large language models",
            "retrieval augmented generation",
            "natural language processing",
            "computer vision convolutional neural network",
            "reinforcement learning",
            "generative adversarial networks",
            "graph neural networks",
            "federated learning",
            "attention mechanism neural networks",
        ]

    articles = []
    seen_ids = set()

    for query in queries:
        print(f"[arXiv] Searching: {query}...")
        search = arxiv.Search(
            query=query,
            max_results=max_results_per_query,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        try:
            for result in search.results():
                if result.entry_id in seen_ids:
                    continue
                seen_ids.add(result.entry_id)

                # Combine title + abstract as content
                text = f"{result.title}\n\n{result.summary}"
                articles.append({
                    "title": result.title,
                    "text": text,
                    "source": "arxiv",
                    "url": result.entry_id,
                    "categories": [c for c in result.categories],
                })
        except Exception as e:
            print(f"[arXiv] Error for '{query}': {e}")
            continue

        time.sleep(1)  # Rate limiting

    print(f"[arXiv] Crawled {len(articles)} abstracts")
    return articles


# ── Simulated Stack Exchange Data ─────────────────────────────────
def generate_synthetic_qa() -> List[Dict]:
    """
    Tạo dữ liệu mô phỏng Stack Exchange AI/CS Q&A.
    Dùng khi không crawl được API trực tiếp.
    """
    qa_pairs = [
        {
            "title": "Difference between CNN and RNN",
            "text": "CNNs (Convolutional Neural Networks) are designed for spatial data like images. They use convolutional filters to extract local features and pooling to reduce dimensions. RNNs (Recurrent Neural Networks) are designed for sequential data like text and time series. They maintain a hidden state that captures temporal dependencies. Key differences: CNNs process data in parallel across spatial dimensions, while RNNs process sequentially. CNNs are translation invariant, RNNs can handle variable-length sequences. Modern architectures like Transformers have largely replaced RNNs for NLP tasks.",
        },
        {
            "title": "What is batch normalization?",
            "text": "Batch normalization is a technique that normalizes the inputs of each layer by adjusting and scaling the activations. During training, it computes the mean and variance of each mini-batch and normalizes the layer's input using these statistics. This helps address the internal covariate shift problem, stabilizes the learning process, and allows higher learning rates. During inference, running averages of mean and variance collected during training are used.",
        },
        {
            "title": "Explain the attention mechanism",
            "text": "The attention mechanism allows neural networks to focus on specific parts of the input when producing output. In the context of transformers, self-attention computes three vectors for each token: Query (Q), Key (K), and Value (V). The attention score between tokens is computed as the dot product of Q and K, scaled by the square root of the dimension, then passed through softmax. This score determines how much each token attends to every other token. Multi-head attention runs multiple attention computations in parallel.",
        },
        {
            "title": "What is transfer learning?",
            "text": "Transfer learning is a machine learning technique where a model trained on one task is repurposed for a different but related task. Instead of training from scratch, the pre-trained model's learned features are used as a starting point. Common approaches include feature extraction (freezing pre-trained layers and training new classifier layers) and fine-tuning (unfreezing some or all pre-trained layers and retraining with a lower learning rate). Popular pre-trained models include ImageNet models for vision and BERT/GPT for NLP.",
        },
        {
            "title": "How does dropout regularization work?",
            "text": "Dropout is a regularization technique that prevents overfitting in neural networks. During training, it randomly sets a fraction of neurons' outputs to zero with probability p (typically 0.5 for hidden layers, 0.2 for input). This forces the network to learn redundant representations and prevents co-adaptation of neurons. During inference, all neurons are active but outputs are scaled by (1-p) to maintain expected values. Variants include spatial dropout for CNNs and DropConnect which drops connections instead of activations.",
        },
        {
            "title": "Explain gradient descent optimization",
            "text": "Gradient descent is the fundamental optimization algorithm for training neural networks. It iteratively updates parameters by moving in the direction of the negative gradient of the loss function. Variants include: SGD (Stochastic Gradient Descent) which uses random mini-batches, Adam which combines momentum and adaptive learning rates, AdaGrad which adapts learning rates per parameter, and RMSProp which uses exponentially decaying average of squared gradients. Learning rate scheduling, warm-up, and gradient clipping are common techniques to improve convergence.",
        },
        {
            "title": "What is a GAN (Generative Adversarial Network)?",
            "text": "A GAN consists of two neural networks trained adversarially: a Generator that creates fake data and a Discriminator that distinguishes real from fake. The Generator tries to fool the Discriminator while the Discriminator tries to correctly classify real vs generated samples. Training reaches Nash equilibrium when the Generator produces data indistinguishable from real data. Variants include DCGAN, StyleGAN, CycleGAN, and Wasserstein GAN. Applications include image generation, super-resolution, data augmentation, and style transfer.",
        },
        {
            "title": "BERT vs GPT: Key differences",
            "text": "BERT (Bidirectional Encoder Representations from Transformers) and GPT (Generative Pre-trained Transformer) represent two fundamental approaches. BERT uses bidirectional encoding with masked language modeling, seeing all tokens simultaneously. It excels at understanding tasks like classification, NER, and QA. GPT uses autoregressive left-to-right decoding, predicting the next token. It excels at generation tasks. BERT is an encoder-only model while GPT is decoder-only. T5 and BART combine both approaches as encoder-decoder models.",
        },
        {
            "title": "What is knowledge distillation?",
            "text": "Knowledge distillation is a model compression technique where a smaller 'student' model learns to mimic a larger 'teacher' model. The student is trained on soft probability distributions (soft targets) produced by the teacher, rather than hard labels. The temperature parameter controls the softness of these distributions. Benefits include reduced model size, faster inference, and maintaining most of the teacher's performance. DistilBERT is a well-known example, achieving 97% of BERT's performance with 40% fewer parameters.",
        },
        {
            "title": "Explain word embeddings: Word2Vec, GloVe, FastText",
            "text": "Word embeddings map words to dense vector representations that capture semantic relationships. Word2Vec (2013) uses either Skip-gram or CBOW to learn embeddings from context windows. GloVe (2014) uses global word co-occurrence statistics from the entire corpus. FastText (2016) represents words as bags of character n-grams, handling out-of-vocabulary words and morphological variations. All produce fixed-dimensional vectors where semantically similar words are close in vector space. Modern contextual embeddings from BERT/GPT have largely superseded these for many tasks.",
        },
    ]

    articles = []
    for qa in qa_pairs:
        articles.append({
            "title": qa["title"],
            "text": qa["text"],
            "source": "stackexchange_synthetic",
            "url": "",
        })

    print(f"[Synthetic] Generated {len(articles)} Q&A pairs")
    return articles


# ── Main Pipeline ─────────────────────────────────────────────────
def crawl_and_chunk(
    use_wikipedia: bool = True,
    use_arxiv: bool = True,
    use_synthetic: bool = True,
    output_file: str = None,
) -> List[Dict]:
    """
    Crawl dữ liệu và chunk thành các đoạn 512 token.
    
    Returns:
        List[Dict] mỗi dict có keys: text, source, title, chunk_id, url
    """
    if output_file is None:
        output_file = str(DATA_DIR / "chunks.json")

    print("=" * 60)
    print("  DATA CRAWLER & CHUNKER")
    print("=" * 60)

    all_articles = []

    if use_wikipedia:
        all_articles.extend(crawl_wikipedia())

    if use_arxiv:
        all_articles.extend(crawl_arxiv())

    if use_synthetic:
        all_articles.extend(generate_synthetic_qa())

    print(f"\nTotal articles: {len(all_articles)}")

    # Chunk
    print("Chunking articles...")
    tokenizer = get_tokenizer()
    chunks = []
    chunk_id = 0

    for article in all_articles:
        article_chunks = chunk_text(article["text"], tokenizer)
        for chunk in article_chunks:
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk,
                "title": article.get("title", ""),
                "source": article["source"],
                "url": article.get("url", ""),
            })
            chunk_id += 1

    print(f"Total chunks: {len(chunks)}")

    # Save
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved to {output_file}")

    return chunks


if __name__ == "__main__":
    chunks = crawl_and_chunk(
        use_wikipedia=True,
        use_arxiv=True,
        use_synthetic=True,
    )
    print(f"\nFinal: {len(chunks)} chunks created")
    if chunks:
        print(f"Sample chunk: {chunks[0]['text'][:100]}...")
