"""LLM Router - Centralized interface for LLM operations

Supports:
- Ollama (local LLM)
- Anthropic Claude (cloud LLM)
- Embedding generation for semantic search
- Text generation for reports
"""

import os
from typing import Optional, List, Dict, Any
from enum import Enum
import ollama
import anthropic
from pydantic_settings import BaseSettings


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """LLM Settings"""
    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # Anthropic settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Default provider
    default_provider: LLMProvider = LLMProvider.OLLAMA

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class LLMRouter:
    """
    Centralized LLM interface supporting multiple providers

    Usage:
        router = LLMRouter()
        response = router.generate("Hello, world!")
        embedding = router.embed("Hello, world!")
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None
    ):
        """
        Initialize LLM Router

        Args:
            provider: LLM provider (OLLAMA or ANTHROPIC)
            model: Model name (uses default if not specified)
        """
        self.provider = provider or settings.default_provider
        self.model = model or self._get_default_model()

        # Initialize clients
        self._init_clients()

    def _get_default_model(self) -> str:
        """Get default model for current provider"""
        if self.provider == LLMProvider.OLLAMA:
            return settings.ollama_model
        elif self.provider == LLMProvider.ANTHROPIC:
            return settings.anthropic_model
        return settings.ollama_model

    def _init_clients(self):
        """Initialize LLM clients"""
        self.ollama_client = ollama.Client(host=settings.ollama_base_url)

        if self.provider == LLMProvider.ANTHROPIC and settings.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            self.anthropic_client = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: Optional[LLMProvider] = None
    ) -> str:
        """
        Generate text using LLM

        Args:
            prompt: User prompt
            system_prompt: System prompt (context)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            provider: Override provider for this call

        Returns:
            Generated text
        """
        provider = provider or self.provider

        if provider == LLMProvider.OLLAMA:
            return self._generate_ollama(prompt, system_prompt, temperature, max_tokens)
        elif provider == LLMProvider.ANTHROPIC:
            return self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate text using Ollama"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.ollama_client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        )

        return response["message"]["content"]

    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate text using Anthropic Claude"""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.anthropic_client.messages.create(**kwargs)

        return response.content[0].text

    def embed(
        self,
        text: str,
        provider: Optional[LLMProvider] = None
    ) -> List[float]:
        """
        Generate embedding for text

        Args:
            text: Text to embed
            provider: Override provider (only OLLAMA supported for embeddings)

        Returns:
            Embedding vector (list of floats)
        """
        # Only Ollama supports embeddings currently
        provider = provider or LLMProvider.OLLAMA

        if provider == LLMProvider.OLLAMA:
            return self._embed_ollama(text)
        else:
            raise ValueError(f"Embeddings not supported for provider: {provider}")

    def _embed_ollama(self, text: str) -> List[float]:
        """Generate embedding using Ollama"""
        response = self.ollama_client.embeddings(
            model=settings.ollama_embed_model,
            prompt=text
        )
        return response["embedding"]

    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """
        Generate structured output (JSON)

        Args:
            prompt: User prompt
            system_prompt: System prompt
            schema: JSON schema for output
            provider: Override provider

        Returns:
            Structured output as dictionary
        """
        # Add JSON format instruction to prompt
        json_instruction = "\n\nIMPORTANT: Respond with valid JSON only, no additional text."
        if schema:
            json_instruction += f"\n\nOutput must follow this schema:\n{schema}"

        response_text = self.generate(
            prompt + json_instruction,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for structured output
            provider=provider
        )

        # Parse JSON response
        import json
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])
            raise ValueError(f"Failed to parse JSON from response: {response_text}")

    def classify_thought(
        self,
        thought: str,
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """
        Classify a thought using LLM

        Args:
            thought: Thought content
            provider: Override provider

        Returns:
            Classification result with type, tags, tickers
        """
        schema = {
            "type": "string (one of: market_view, stock_idea, risk_concern, ai_insight, content_note, general)",
            "tags": ["array of strings"],
            "tickers": ["array of stock ticker symbols"]
        }

        prompt = f"Classify this investment-related thought:\n\n{thought}"

        return self.generate_structured(
            prompt=prompt,
            schema=schema,
            provider=provider
        )

    def summarize_content(
        self,
        content: str,
        max_length: int = 300,
        provider: Optional[LLMProvider] = None
    ) -> str:
        """
        Summarize content using LLM

        Args:
            content: Content to summarize
            max_length: Maximum length of summary
            provider: Override provider

        Returns:
            Summary text
        """
        prompt = f"""Summarize the following content in Korean, within {max_length} characters.
Focus on key insights and actionable information.

Content:
{content}"""

        return self.generate(prompt, provider=provider)

    def extract_entities(
        self,
        text: str,
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """
        Extract entities from text (tickers, companies, topics)

        Args:
            text: Text to analyze
            provider: Override provider

        Returns:
            Extracted entities
        """
        schema = {
            "tickers": ["array of stock ticker symbols"],
            "companies": ["array of company names"],
            "topics": ["array of topics/keywords"],
            "sentiment": "string (bullish, bearish, neutral)"
        }

        prompt = f"""Extract entities from the following text:
- Stock tickers (e.g., AAPL, 005930.KS)
- Company names
- Topics/keywords
- Overall sentiment (bullish, bearish, neutral)

Text:
{text}"""

        return self.generate_structured(
            prompt=prompt,
            schema=schema,
            provider=provider
        )


# ──── Convenience Functions ────
def get_llm_router(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None
) -> LLMRouter:
    """Get LLM Router instance"""
    return LLMRouter(provider=provider, model=model)


def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: Optional[LLMProvider] = None
) -> str:
    """Quick text generation"""
    router = get_llm_router(provider=provider)
    return router.generate(prompt, system_prompt=system_prompt)


def get_embedding(text: str) -> List[float]:
    """Quick embedding generation"""
    router = get_llm_router()
    return router.embed(text)


def classify_thought(thought: str) -> Dict[str, Any]:
    """Quick thought classification"""
    router = get_llm_router()
    return router.classify_thought(thought)
