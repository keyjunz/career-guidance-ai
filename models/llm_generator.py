"""
LLM Generator module — Sinh câu trả lời từ context + question.
Hỗ trợ: Qwen2.5-3B, Gemma-2-2B, Phi-3-mini (qua Transformers + bitsandbytes 4-bit)
"""

import time
import gc
import numpy as np
from pathlib import Path
from typing import Optional, Dict

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    pipeline,
)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    LLM_MODELS, DEFAULT_LLM, DEVICE,
    RAG_PROMPT_TEMPLATE, RAG_PROMPT_TEMPLATE_VI, MAX_ANSWER_WORDS,
)


class LLMGenerator:
    """
    LLM-based answer generator with 4-bit quantization support.
    """

    def __init__(self, model_key: str = DEFAULT_LLM, device: str = DEVICE):
        self.model_key = model_key
        self.model_config = LLM_MODELS[model_key]
        self.model_name = self.model_config["name"]
        self.max_new_tokens = self.model_config["max_new_tokens"]
        self.temperature = self.model_config["temperature"]
        self.top_p = self.model_config["top_p"]
        self.quantization = self.model_config["quantization"]
        self.device = device

        self.tokenizer = None
        self.model = None
        self.pipe = None
        self._loaded = False

    def load(self):
        """Load model và tokenizer."""
        if self._loaded:
            print(f"[LLM] {self.model_name} already loaded.")
            return

        print(f"[LLM] Loading {self.model_name} (quantization={self.quantization})...")

        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Quantization config
        if self.quantization == "4bit" and self.device == "cuda":
            try:
                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quant_config,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                )
            except Exception as e:
                print(f"[LLM] 4-bit quantization failed: {e}. Falling back to float16...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="cuda",
                    trust_remote_code=True,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                )
        elif self.quantization == "8bit" and self.device == "cuda":
            try:
                quant_config = BitsAndBytesConfig(load_in_8bit=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quant_config,
                    device_map="auto",
                    trust_remote_code=True,
                    low_cpu_mem_usage=True,
                )
            except Exception as e:
                print(f"[LLM] 8-bit quantization failed: {e}. Falling back to float16...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="cuda",
                    trust_remote_code=True,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                )
        elif self.device == "cuda":
            # float16 trực tiếp lên GPU — tránh hoàn toàn paging file
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="cuda",
                trust_remote_code=True,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
            )
        else:
            # CPU fallback
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )

        # Pipeline
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        )

        self._loaded = True
        vram = self._get_gpu_memory_mb()
        print(f"[LLM] Loaded. GPU Memory used: ~{vram:.0f} MB")

    def generate(
        self,
        question: str,
        context: str,
        language: str = "en",
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict:
        """
        Sinh câu trả lời từ context + question.

        Args:
            question: Câu hỏi người dùng
            context: Đoạn context từ retriever+reranker
            language: 'en' hoặc 'vi'
            max_new_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            Dict: {'answer': str, 'latency_ms': float, 'tokens_generated': int}
        """
        if not self._loaded:
            self.load()

        # Chọn template
        template = RAG_PROMPT_TEMPLATE_VI if language == "vi" else RAG_PROMPT_TEMPLATE
        prompt = template.format(context=context, question=question)

        max_tok = max_new_tokens or self.max_new_tokens
        temp = temperature or self.temperature

        start = time.perf_counter()

        # Dùng chat template nếu model hỗ trợ
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.chat_template:
            messages = [{"role": "user", "content": prompt}]
            outputs = self.pipe(
                messages,
                max_new_tokens=max_tok,
                temperature=temp,
                top_p=self.top_p,
                do_sample=temp > 0,
                return_full_text=False,
            )
            answer = outputs[0]["generated_text"]
            if isinstance(answer, list) and len(answer) > 0:
                answer = answer[0].get("content", str(answer))
        else:
            outputs = self.pipe(
                prompt,
                max_new_tokens=max_tok,
                temperature=temp,
                top_p=self.top_p,
                do_sample=temp > 0,
                return_full_text=False,
            )
            answer = outputs[0]["generated_text"]

        latency = (time.perf_counter() - start) * 1000

        # Đếm token sinh ra
        tokens_gen = len(self.tokenizer.encode(answer))

        # Cắt nếu vượt MAX_ANSWER_WORDS
        words = answer.split()
        if len(words) > MAX_ANSWER_WORDS:
            answer = " ".join(words[:MAX_ANSWER_WORDS]) + "..."

        return {
            "answer": answer.strip(),
            "latency_ms": latency,
            "tokens_generated": tokens_gen,
            "tokens_per_second": tokens_gen / (latency / 1000) if latency > 0 else 0,
        }

    def benchmark_latency(
        self,
        n_runs: int = 5,
        question: str = "What is the transformer architecture?",
        context: str = "The Transformer is a deep learning model architecture introduced in "
                       "'Attention Is All You Need' by Vaswani et al. It relies on self-attention "
                       "mechanisms to process sequential data without recurrence.",
    ):
        """Đo latency generation."""
        if not self._loaded:
            self.load()

        latencies = []
        tok_per_sec = []

        for i in range(n_runs):
            result = self.generate(question, context)
            latencies.append(result["latency_ms"])
            tok_per_sec.append(result["tokens_per_second"])

        avg_lat = np.mean(latencies)
        avg_tps = np.mean(tok_per_sec)
        print(f"[Benchmark LLM] {self.model_name}")
        print(f"  Avg latency: {avg_lat:.0f}ms | Avg tokens/s: {avg_tps:.1f}")
        return {"avg_latency_ms": avg_lat, "avg_tokens_per_second": avg_tps}

    def unload(self):
        """Giải phóng bộ nhớ GPU."""
        if self.model is not None:
            del self.model
            del self.pipe
            self.model = None
            self.pipe = None
            self._loaded = False
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("[LLM] Model unloaded, GPU memory freed.")

    def _get_gpu_memory_mb(self) -> float:
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 ** 2)
        return 0


class APILLMGenerator:
    """
    LLM Generator sử dụng API (Groq / Gemini) thay vì self-host.
    Không cần GPU, inference nhanh, model mạnh hơn.
    """

    def __init__(self, model_key: str = None):
        from config import (
            API_LLM_MODELS, DEFAULT_API_LLM,
            GROQ_API_KEY, GEMINI_API_KEY,
        )
        self.model_key = model_key or DEFAULT_API_LLM
        self.model_config = API_LLM_MODELS[self.model_key]
        self.provider = self.model_config["provider"]
        self.model_name = self.model_config["name"]
        self.max_tokens = self.model_config["max_tokens"]
        self.temperature = self.model_config["temperature"]

        self.client = None
        self._loaded = False

        # Resolve API key
        if self.provider == "groq":
            self.api_key = GROQ_API_KEY
        elif self.provider == "gemini":
            self.api_key = GEMINI_API_KEY
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        if not self.api_key:
            print(f"[API LLM] ⚠️  {self.model_config['api_key_env']} not set!")
            print(f"  → Set it in .env file or environment variable")

    def load(self):
        """Initialize API client."""
        if self._loaded:
            return

        if self.provider == "groq":
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                print(f"[API LLM] ✅ Groq client ready — model: {self.model_name}")
            except ImportError:
                raise ImportError("groq package not installed. Run: pip install groq")

        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                print(f"[API LLM] ✅ Gemini client ready — model: {self.model_name}")
            except ImportError:
                raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

        self._loaded = True

    def generate(
        self,
        question: str,
        context: str,
        language: str = "en",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict:
        """
        Sinh câu trả lời qua API.
        Interface giống hệt LLMGenerator.generate() để pipeline dùng chung.
        """
        if not self._loaded:
            self.load()

        template = RAG_PROMPT_TEMPLATE_VI if language == "vi" else RAG_PROMPT_TEMPLATE
        prompt = template.format(context=context, question=question)

        max_tok = max_tokens or self.max_tokens
        temp = temperature or self.temperature

        start = time.perf_counter()
        
        # 🔄 Retry Logic (Tối đa 3 lần)
        max_retries = 3
        retry_delay = 1.5

        for attempt in range(max_retries):
            try:
                if self.provider == "groq":
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tok,
                        temperature=temp,
                    )
                    answer = response.choices[0].message.content
                    tokens_gen = response.usage.completion_tokens if response.usage else len(answer.split())

                elif self.provider == "gemini":
                    response = self.client.generate_content(
                        prompt,
                        generation_config={
                            "max_output_tokens": max_tok,
                            "temperature": temp,
                        },
                    )
                    answer = response.text
                    tokens_gen = len(answer.split())  # Gemini không trả exact token count
                
                break # Nếu thành công thì thoát vòng lặp retry

            except Exception as e:
                print(f"[API LLM] ⚠️ Lỗi gọi API (lần {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    answer = f"[API Error] Đã thử {max_retries} lần nhưng thất bại: {str(e)}"
                    tokens_gen = 0

        latency = (time.perf_counter() - start) * 1000

        # Truncate nếu quá dài
        words = answer.split()
        if len(words) > MAX_ANSWER_WORDS:
            answer = " ".join(words[:MAX_ANSWER_WORDS]) + "..."

        return {
            "answer": answer.strip(),
            "latency_ms": latency,
            "tokens_generated": tokens_gen,
            "tokens_per_second": tokens_gen / (latency / 1000) if latency > 0 else 0,
            "provider": self.provider,
            "model": self.model_name,
        }

    def unload(self):
        """API client không cần giải phóng GPU."""
        self.client = None
        self._loaded = False
        print(f"[API LLM] Client closed.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", action="store_true", help="Test API LLM instead of local")
    parser.add_argument("--model", type=str, default=None, help="API model key")
    args = parser.parse_args()

    print("=" * 50)

    context = """The Transformer architecture was introduced in 2017 by Vaswani et al. 
    It uses self-attention mechanisms instead of recurrence to process sequences.
    Key components include multi-head attention, positional encoding, and feed-forward layers.
    Transformers have become the foundation for models like BERT, GPT, and T5."""

    if args.api:
        print(" API LLM GENERATOR TEST")
        print("=" * 50)

        llm = APILLMGenerator(model_key=args.model)
        llm.load()

        result = llm.generate(
            question="What are the key components of the Transformer architecture?",
            context=context,
            language="en",
        )
        print(f"\n[EN] Answer: {result['answer'][:300]}...")
        print(f"  Provider: {result['provider']} | Model: {result['model']}")
        print(f"  Latency: {result['latency_ms']:.0f}ms | Tokens: {result['tokens_generated']}")

        result_vi = llm.generate(
            question="Kiến trúc Transformer có những thành phần chính nào?",
            context=context,
            language="vi",
        )
        print(f"\n[VI] Answer: {result_vi['answer'][:300]}...")
        print(f"  Latency: {result_vi['latency_ms']:.0f}ms | Tokens: {result_vi['tokens_generated']}")

    else:
        print(" LOCAL LLM GENERATOR TEST")
        print("=" * 50)

        llm = LLMGenerator()
        llm.load()

        result = llm.generate(
            question="What are the key components of the Transformer architecture?",
            context=context,
            language="en",
        )
        print(f"\n[EN] Answer: {result['answer'][:200]}...")
        print(f"  Latency: {result['latency_ms']:.0f}ms | Tokens: {result['tokens_generated']} | Speed: {result['tokens_per_second']:.1f} tok/s")

        result_vi = llm.generate(
            question="Kiến trúc Transformer có những thành phần chính nào?",
            context=context,
            language="vi",
        )
        print(f"\n[VI] Answer: {result_vi['answer'][:200]}...")
        print(f"  Latency: {result_vi['latency_ms']:.0f}ms | Tokens: {result_vi['tokens_generated']} | Speed: {result_vi['tokens_per_second']:.1f} tok/s")
