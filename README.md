# RAG Chatbot

Module RAG core cho he thong chatbot hoi dap chuyen nganh Computer Science.

Trang thai hien tai cua codebase:

- Runtime query hien tai dung hybrid retriever `FAISS + BM25`.
- Co ho tro build Chroma DB, nhung `rag_pipeline.py` chua dung Chroma lam backend truy van runtime.
- Mac dinh dung API LLM, khong phai local LLM.
- Co ho tro auto-detect ngon ngu VI/EN va dich query tieng Viet sang tieng Anh truoc khi retrieval.

## Kien truc hien tai

Pipeline end-to-end:

1. `data_crawler.py`
   Crawl du lieu tu Wikipedia, arXiv va synthetic QA, sau do chunk thanh `data/chunks.json`.
2. `build_vectordb.py`
   Sinh embeddings, cache embeddings, build va save retriever index.
3. `rag_pipeline.py`
   Load embedding model, retriever, reranker, LLM, sau do tra loi cau hoi.
4. `evaluate.py`
   Chay evaluation voi BLEU, ROUGE-L, F1, latency va heuristic hallucination rate.
5. `benchmark.py`
   Do latency va memory cho tung component.

## Entry Points

- `config.py`: cau hinh tap trung cho models, thresholds, prompts, paths, API keys.
- `data_crawler.py`: crawl va chunk corpus.
- `build_vectordb.py`: build FAISS/BM25, tuy chon build them Chroma.
- `rag_pipeline.py`: CLI query va interactive chat.
- `evaluate.py`: tao QA dataset va cham diem pipeline.
- `benchmark.py`: benchmark embedding, retriever, reranker, LLM.

## Yeu cau moi truong

- Python `3.10`
- Khuyen nghi dung conda env rieng:

```bash
conda create -n rag310 python=3.10
conda activate rag310
pip install -r requirements.txt
```

Neu ban dang dung Python 3.7 hoac 3.8, nhieu dependency se khong cai hoac chay on dinh.

## Dependencies chinh

File [requirements.txt](/D:/Documents/RAG_chatbot/requirements.txt) da duoc dong bo voi code hien tai, bao gom:

- Core ML: `torch`, `transformers`, `sentence-transformers`
- Retrieval: `faiss-cpu`, `chromadb`, `rank-bm25`
- Evaluation: `rouge-score`, `nltk`
- Crawling: `wikipedia-api`, `arxiv`, `datasets`
- Utilities: `python-dotenv`, `psutil`, `tqdm`, `langdetect`
- API LLM: `groq`, `google-generativeai`

## Cau hinh API

Copy `.env.example` thanh `.env` va dien API key:

```env
GROQ_API_KEY=gsk_your_key_here
GEMINI_API_KEY=AIzaSy_your_key_here
```

Code hien tai mac dinh:

- `USE_API_LLM = True`
- `DEFAULT_API_LLM = "groq-llama3-70b"`
- `DEFAULT_LLM = "qwen2.5-1.5b"` chi duoc dung khi bat local mode

Xem chi tiet tai [config.py](/D:/Documents/RAG_chatbot/config.py).

## Cach chay

### 1. Crawl va chunk du lieu

```bash
python data_crawler.py
```

Output:

- `data/chunks.json`

### 2. Build retriever index

Build backend runtime hien tai:

```bash
python build_vectordb.py --backend faiss
```

Build Chroma de test hoac chuan bi cho integration:

```bash
python build_vectordb.py --backend chroma
```

Build ca hai:

```bash
python build_vectordb.py --backend both
```

Output chinh cho runtime hien tai:

- `indexes/retriever_faiss.index`
- `indexes/retriever_bm25.pkl`
- `indexes/retriever_docs.json`

### 3. Chay RAG pipeline

Query don:

```bash
python rag_pipeline.py --query "What is the transformer architecture?"
```

Interactive mode:

```bash
python rag_pipeline.py --interactive
```

Ep local LLM:

```bash
python rag_pipeline.py --query "Explain backpropagation" --use-local
```

Chon API model:

```bash
python rag_pipeline.py --query "What is RAG?" --use-api --api-model groq-llama3-8b
```

Luu y:

- Neu khong co index da build truoc, pipeline se canh bao va retrieval se khong dung duoc.
- `--language` hien tai chi nhan `en` hoac `vi`. Interactive mode tu auto-detect ngon ngu.

## Evaluation

Tao QA dataset tu corpus bang API LLM:

```bash
python evaluate.py --create-dataset --max-questions 12
```

Chay evaluation:

```bash
python evaluate.py --max-questions 12
```

Output:

- `results/evaluation_results.json`

## Benchmark

```bash
python benchmark.py --component embedding
python benchmark.py --component retriever
python benchmark.py --component reranker
python benchmark.py --component llm
python benchmark.py --component all
```

Luu y: `benchmark.py` ho tro `all`, khong phai `full`.

## Ghi chu ky thuat

- Chunking dung tokenizer `bert-base-uncased`, nen token count la xap xi voi generator/embedding model.
- Heuristic hallucination trong `evaluate.py` rat don gian, khong nen xem la metric chat luong cuoi cung.
- Chroma da co trong module indexing, nhung runtime query van dang load retriever FAISS/BM25.

## Quy trinh xac nhan clean start duoc khuyen nghi

1. Tao moi truong Python 3.10 moi.
2. `pip install -r requirements.txt`
3. `python data_crawler.py`
4. `python build_vectordb.py --backend faiss`
5. `python rag_pipeline.py --query "What is RAG?"`
6. `python evaluate.py --max-questions 3`

Neu muon xac nhan local LLM, chay them:

```bash
python rag_pipeline.py --query "What is attention?" --use-local
```
