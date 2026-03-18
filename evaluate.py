"""
Evaluate — Đánh giá hiệu năng RAG pipeline.
Chỉ số: BLEU, ROUGE-L, F1, hallucination rate.
"""

import json
import re
import time
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    RESULTS_DIR, DATA_DIR,
    BLEU_THRESHOLD, ROUGE_L_THRESHOLD, HALLUCINATION_THRESHOLD,
)

from rouge_score import rouge_scorer
import nltk
try:
    # Cần thiết cho BLEU/ROUGE split tokens
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except Exception:
    pass
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction


# ── Sample QA Dataset ─────────────────────────────────────────────
def create_sample_qa_dataset(output_file: str = None) -> List[Dict]:
    """
    Tạo tập QA AI/CS mẫu cho evaluation.
    Thực tế nên có 500 câu, đây là 50 câu mẫu đại diện.
    """
    if output_file is None:
        output_file = str(DATA_DIR / "qa_test.json")

    qa_data = [
        {
            "id": 1,
            "question": "What is a neural network?",
            "reference_answer": "A neural network is a computing system inspired by biological neural networks. It consists of interconnected nodes (neurons) organized in layers that process information using connectionist approaches. Neural networks learn by adjusting connection weights through training on data.",
            "category": "fundamentals"
        },
        {
            "id": 2,
            "question": "How does backpropagation work?",
            "reference_answer": "Backpropagation computes gradients of the loss function with respect to each weight by applying the chain rule. It propagates errors backward from the output layer through hidden layers, computing partial derivatives at each layer to determine how each weight should be adjusted to minimize the loss.",
            "category": "optimization"
        },
        {
            "id": 3,
            "question": "What is the transformer architecture?",
            "reference_answer": "The Transformer is a deep learning architecture introduced by Vaswani et al. in 2017. It uses self-attention mechanisms instead of recurrence to process sequences. Key components include multi-head attention, positional encoding, feed-forward layers, and layer normalization. It forms the basis for models like BERT and GPT.",
            "category": "architecture"
        },
        {
            "id": 4,
            "question": "Explain the attention mechanism in deep learning.",
            "reference_answer": "The attention mechanism allows models to focus on relevant parts of the input. In transformers, it computes Query, Key, and Value vectors for each token. Attention scores are calculated as scaled dot products of Q and K, passed through softmax, then used to weight V vectors. Multi-head attention runs multiple attention computations in parallel.",
            "category": "architecture"
        },
        {
            "id": 5,
            "question": "What is transfer learning?",
            "reference_answer": "Transfer learning is a technique where a model trained on one task is repurposed for a different but related task. It leverages pre-trained knowledge, reducing training time and data requirements. Common approaches include feature extraction and fine-tuning of pre-trained models.",
            "category": "techniques"
        },
        {
            "id": 6,
            "question": "How does gradient descent optimize neural networks?",
            "reference_answer": "Gradient descent iteratively updates model parameters by moving in the direction of the negative gradient of the loss function. Variants include SGD with mini-batches, Adam which combines momentum and adaptive learning rates, and learning rate scheduling for better convergence.",
            "category": "optimization"
        },
        {
            "id": 7,
            "question": "What is the difference between supervised and unsupervised learning?",
            "reference_answer": "Supervised learning trains models using labeled data with input-output pairs, used for classification and regression. Unsupervised learning finds patterns in unlabeled data, used for clustering, dimensionality reduction, and anomaly detection. Semi-supervised learning combines both approaches.",
            "category": "fundamentals"
        },
        {
            "id": 8,
            "question": "Explain convolutional neural networks (CNNs).",
            "reference_answer": "CNNs are neural networks designed for processing grid-like data such as images. They use convolutional layers with learnable filters to extract features, pooling layers to reduce spatial dimensions, and fully connected layers for classification. Key properties include local connectivity, weight sharing, and translation invariance.",
            "category": "architecture"
        },
        {
            "id": 9,
            "question": "What is BERT and how does it work?",
            "reference_answer": "BERT (Bidirectional Encoder Representations from Transformers) is a pre-trained language model that uses bidirectional self-attention to understand context. It is pre-trained with masked language modeling and next sentence prediction tasks. BERT can be fine-tuned for various NLP tasks like classification, NER, and question answering.",
            "category": "nlp"
        },
        {
            "id": 10,
            "question": "How does reinforcement learning work?",
            "reference_answer": "Reinforcement learning trains agents to make decisions by interacting with an environment. The agent receives rewards or penalties for its actions and learns a policy to maximize cumulative reward. Key concepts include states, actions, rewards, policy, and value functions. Algorithms include Q-learning, policy gradient methods, and actor-critic approaches.",
            "category": "fundamentals"
        },
        {
            "id": 11,
            "question": "What are generative adversarial networks (GANs)?",
            "reference_answer": "GANs consist of two networks: a Generator that creates synthetic data and a Discriminator that distinguishes real from fake data. They are trained adversarially in a minimax game. Applications include image generation, style transfer, and data augmentation.",
            "category": "architecture"
        },
        {
            "id": 12,
            "question": "Explain word embeddings like Word2Vec.",
            "reference_answer": "Word embeddings are dense vector representations of words that capture semantic relationships. Word2Vec uses Skip-gram or CBOW architectures to learn from context windows. Similar words have similar vectors, enabling analogical reasoning like king - man + woman = queen.",
            "category": "nlp"
        },
        {
            "id": 13,
            "question": "What is dropout regularization?",
            "reference_answer": "Dropout randomly deactivates neurons during training with a probability p, preventing overfitting and co-adaptation. During inference, all neurons are active but outputs are scaled. It acts as an ensemble method, training many sub-networks implicitly.",
            "category": "techniques"
        },
        {
            "id": 14,
            "question": "How does batch normalization work?",
            "reference_answer": "Batch normalization normalizes layer inputs by subtracting the batch mean and dividing by the batch standard deviation. It includes learnable scale and shift parameters. This stabilizes training, allows higher learning rates, and acts as a regularizer.",
            "category": "techniques"
        },
        {
            "id": 15,
            "question": "What is the vanishing gradient problem?",
            "reference_answer": "The vanishing gradient problem occurs when gradients become extremely small during backpropagation through many layers, making it difficult to update early layer weights. Solutions include ReLU activation functions, residual connections, batch normalization, and LSTM/GRU architectures.",
            "category": "optimization"
        },
        {
            "id": 16,
            "question": "Explain recurrent neural networks (RNNs).",
            "reference_answer": "RNNs process sequential data by maintaining a hidden state that captures information from previous time steps. They share weights across time steps. Variants like LSTM and GRU address the vanishing gradient problem with gating mechanisms. Applications include language modeling and time series prediction.",
            "category": "architecture"
        },
        {
            "id": 17,
            "question": "What is knowledge distillation?",
            "reference_answer": "Knowledge distillation compresses a large teacher model into a smaller student model by training the student to match the teacher's soft probability outputs. The temperature parameter controls output softness. DistilBERT achieves 97% of BERT's performance with 40% fewer parameters.",
            "category": "techniques"
        },
        {
            "id": 18,
            "question": "How does the GPT model generate text?",
            "reference_answer": "GPT uses autoregressive left-to-right decoding with a transformer decoder architecture. It predicts the next token based on all previous tokens using masked self-attention. Pre-trained on large text corpora, it can be fine-tuned or used with prompting for various generation tasks.",
            "category": "nlp"
        },
        {
            "id": 19,
            "question": "What is retrieval-augmented generation (RAG)?",
            "reference_answer": "RAG combines information retrieval with text generation. It first retrieves relevant documents from a knowledge base using similarity search, then passes the retrieved context to a language model for answer generation. This reduces hallucination and allows grounding responses in specific knowledge.",
            "category": "techniques"
        },
        {
            "id": 20,
            "question": "Explain the concept of overfitting in machine learning.",
            "reference_answer": "Overfitting occurs when a model learns noise and specific patterns in training data that don't generalize to new data. Signs include high training accuracy but low test accuracy. Prevention methods include regularization, cross-validation, early stopping, data augmentation, and dropout.",
            "category": "fundamentals"
        },
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(qa_data, f, ensure_ascii=False, indent=2)
    print(f"Created QA test dataset: {len(qa_data)} questions → {output_file}")
    return qa_data


# ── Metrics ───────────────────────────────────────────────────────
def compute_bleu(reference: str, hypothesis: str) -> float:
    """Compute BLEU score (0-100)."""
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not hyp_tokens:
        return 0.0
    smoothing = SmoothingFunction().method1
    try:
        score = sentence_bleu([ref_tokens], hyp_tokens, smoothing_function=smoothing)
    except Exception:
        score = 0.0
    return score * 100


def compute_rouge_l(reference: str, hypothesis: str) -> float:
    """Compute ROUGE-L F1 score (0-100)."""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return scores["rougeL"].fmeasure * 100


def compute_f1(reference: str, hypothesis: str) -> float:
    """Compute token-level F1 score (0-100)."""
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    common = Counter(ref_tokens) & Counter(hyp_tokens)
    num_common = sum(common.values())
    if num_common == 0:
        return 0.0
    precision = num_common / len(hyp_tokens)
    recall = num_common / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1 * 100


def detect_hallucination(answer: str, context: str, threshold: float = 0.3) -> Tuple[bool, float]:
    """
    Phát hiện hallucination đơn giản bằng cách kiểm tra overlap giữa answer và context.
    Nếu answer chứa nhiều thông tin không có trong context → hallucination.
    """
    answer_sentences = re.split(r'[.!?]+', answer.lower())
    answer_sentences = [s.strip() for s in answer_sentences if len(s.strip()) > 10]

    if not answer_sentences:
        return False, 0.0

    context_lower = context.lower()
    hallucinated = 0
    for sent in answer_sentences:
        words = sent.split()
        if len(words) < 3:
            continue
        # Check if key phrases from the sentence appear in context
        overlap = sum(1 for w in words if w in context_lower) / len(words)
        if overlap < threshold:
            hallucinated += 1

    rate = hallucinated / len(answer_sentences) if answer_sentences else 0.0
    return rate > HALLUCINATION_THRESHOLD, rate


# ── Evaluation Runner ─────────────────────────────────────────────
def evaluate_pipeline(
    pipeline,
    qa_file: str = None,
    output_file: str = None,
    language: str = "en",
    max_questions: int = None,
):
    """
    Chạy evaluation trên tập QA.
    """
    if qa_file is None:
        qa_file = str(DATA_DIR / "qa_test.json")
    if output_file is None:
        output_file = str(RESULTS_DIR / "evaluation_results.json")

    # Load or create QA data
    qa_path = Path(qa_file)
    if not qa_path.exists():
        print(f"QA file not found. Creating sample dataset...")
        qa_data = create_sample_qa_dataset(str(qa_path))
    else:
        with open(qa_path, "r", encoding="utf-8") as f:
            qa_data = json.load(f)

    if max_questions:
        qa_data = qa_data[:max_questions]

    print(f"\n{'=' * 60}")
    print(f"  EVALUATION — {len(qa_data)} questions")
    print(f"{'=' * 60}")

    results = []
    all_bleu = []
    all_rouge_l = []
    all_f1 = []
    all_latency = []
    hallucination_count = 0

    for i, qa in enumerate(qa_data):
        print(f"\n[{i+1}/{len(qa_data)}] {qa['question'][:50]}...")

        # Run pipeline
        result = pipeline.query(
            question=qa["question"],
            language=language,
            verbose=False,
        )

        answer = result["answer"]
        reference = qa["reference_answer"]
        context = result.get("context", "")

        # Compute metrics
        bleu = compute_bleu(reference, answer)
        rouge_l = compute_rouge_l(reference, answer)
        f1 = compute_f1(reference, answer)
        is_hallucinated, halluc_rate = detect_hallucination(answer, context)

        all_bleu.append(bleu)
        all_rouge_l.append(rouge_l)
        all_f1.append(f1)
        all_latency.append(result["latency"]["total_ms"])
        if is_hallucinated:
            hallucination_count += 1

        results.append({
            "id": qa["id"],
            "question": qa["question"],
            "reference": reference,
            "generated": answer,
            "bleu": float(round(bleu, 2)),
            "rouge_l": float(round(rouge_l, 2)),
            "f1": float(round(f1, 2)),
            "hallucination_rate": float(round(halluc_rate, 3)),
            "is_hallucinated": bool(is_hallucinated),
            "latency_ms": float(round(result["latency"]["total_ms"], 1)),
            "category": qa.get("category", ""),
        })

        print(f"  BLEU={bleu:.1f} | ROUGE-L={rouge_l:.1f} | F1={f1:.1f} | "
              f"Halluc={halluc_rate:.2f} | Latency={result['latency']['total_ms']:.0f}ms")

    # Summary
    summary = {
        "total_questions": len(qa_data),
        "avg_bleu": float(round(np.mean(all_bleu), 2)),
        "avg_rouge_l": float(round(np.mean(all_rouge_l), 2)),
        "avg_f1": float(round(np.mean(all_f1), 2)),
        "avg_latency_ms": float(round(np.mean(all_latency), 1)),
        "p95_latency_ms": float(round(np.percentile(all_latency, 95), 1)),
        "hallucination_rate": float(round(hallucination_count / len(qa_data), 3)),
        "pass_bleu": bool(np.mean(all_bleu) >= BLEU_THRESHOLD),
        "pass_rouge_l": bool(np.mean(all_rouge_l) >= ROUGE_L_THRESHOLD),
        "pass_hallucination": bool((hallucination_count / len(qa_data)) < HALLUCINATION_THRESHOLD),
    }

    output = {"summary": summary, "results": results}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  EVALUATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Questions:           {summary['total_questions']}")
    print(f"  Avg BLEU:            {summary['avg_bleu']:.2f}  {'✅' if summary['pass_bleu'] else '❌'} (threshold: {BLEU_THRESHOLD})")
    print(f"  Avg ROUGE-L:         {summary['avg_rouge_l']:.2f}  {'✅' if summary['pass_rouge_l'] else '❌'} (threshold: {ROUGE_L_THRESHOLD})")
    print(f"  Avg F1:              {summary['avg_f1']:.2f}")
    print(f"  Hallucination Rate:  {summary['hallucination_rate']:.1%}  {'✅' if summary['pass_hallucination'] else '❌'} (threshold: {HALLUCINATION_THRESHOLD:.0%})")
    print(f"  Avg Latency:         {summary['avg_latency_ms']:.0f}ms")
    print(f"  P95 Latency:         {summary['p95_latency_ms']:.0f}ms")
    print(f"\n  Results saved to: {output_file}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG Pipeline")
    parser.add_argument("--qa-file", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument("--create-dataset", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    if args.create_dataset:
        create_sample_qa_dataset()
    else:
        from rag_pipeline import RAGPipeline
        rag = RAGPipeline(load_llm=not args.no_llm)
        evaluate_pipeline(
            pipeline=rag,
            qa_file=args.qa_file,
            output_file=args.output,
            max_questions=args.max_questions,
        )
