"""
LLM Client abstraction for ARIA.
Supports Groq Cloud (ultra-fast Llama 3.3 70B) and Local Ollama (zero-cost offline).
"""

import os
from typing import List, Dict, Any, Optional
import httpx
from aria import config


class LLMClient:
    """
    Unified LLM Client that provides structured text generation
    across Groq and Ollama backends.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = (provider or config.LLM_PROVIDER).lower().strip()
        self.api_key = api_key or config.GROQ_API_KEY
        self.groq_model = model or config.GROQ_MODEL
        self.ollama_model = model or config.OLLAMA_MODEL
        self.ollama_base_url = config.OLLAMA_BASE_URL.rstrip("/")

        # Auto-switch to Ollama if Groq is requested but no key is set and Ollama is available
        if self.provider == "groq" and not self.api_key:
            if self._is_ollama_available():
                print("[ARIA Info] No GROQ_API_KEY detected. Automatically using local Ollama model.")
                self.provider = "ollama"
            else:
                print(
                    "[ARIA Warning] GROQ_API_KEY is not set. Please get a free key from https://console.groq.com/keys "
                    "or start Ollama with 'ollama serve'."
                )

        self._groq_client = None
        if self.provider == "groq" and self.api_key:
            from groq import Groq
            self._groq_client = Groq(api_key=self.api_key)

    def _is_ollama_available(self) -> bool:
        """Check if local Ollama server is responding."""
        try:
            r = httpx.get(f"{self.ollama_base_url}/models", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    @property
    def active_model(self) -> str:
        """Return the active model name."""
        if self.provider == "groq":
            return self.groq_model
        return self.ollama_model

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate a completion given a list of chat messages.
        messages format: [{'role': 'system'|'user'|'assistant', 'content': '...'}]
        """
        if self.provider == "groq":
            return self._generate_groq(messages, temperature, max_tokens)
        elif self.provider == "ollama":
            return self._generate_ollama(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported LLM provider: '{self.provider}'. Supported: 'groq', 'ollama'")

    def _generate_groq(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self._groq_client:
            # Try re-initializing if key was provided in runtime
            if self.api_key:
                from groq import Groq
                self._groq_client = Groq(api_key=self.api_key)
            else:
                raise ValueError(
                    "GROQ_API_KEY is not set! Set GROQ_API_KEY in your .env file or use --provider ollama"
                )

        try:
            response = self._groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Groq API error: {str(e)}")

    def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self.ollama_base_url}/chat/completions"
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            response = httpx.post(url, json=payload, timeout=float(config.TIMEOUT_SECONDS))
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama API returned status {response.status_code}: {response.text}"
                )
            data = response.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content") or ""
            # If content is empty (e.g., thinking models consumed output in reasoning), fallback to reasoning
            if not content.strip() and choice.get("reasoning"):
                content = choice.get("reasoning") or ""
            return content
        except httpx.ConnectError:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.ollama_base_url}. Is 'ollama serve' running?"
            )
        except httpx.ReadTimeout:
            raise RuntimeError(
                f"Ollama inference timed out after {config.TIMEOUT_SECONDS}s. Try a smaller/faster model like 'llama2-uncensored:7b' or increase TIMEOUT_SECONDS."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama inference error: {str(e)}")
