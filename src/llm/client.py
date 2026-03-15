"""
LLM Client for DMFB Agent System

Supports multiple LLM providers:
- Kimi (Moonshot AI)
- OpenAI
- Anthropic (Claude)

Author: Claude
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass, field
from enum import Enum
import requests


class LLMProvider(Enum):
    """Supported LLM providers."""
    KIMI = "kimi"           # Moonshot AI
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration for LLM client."""
    provider: LLMProvider = LLMProvider.KIMI
    api_key: str = None
    base_url: str = None
    model: str = "moonshot-v1-8k"  # Default for Kimi
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    retry_count: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        if self.api_key is None:
            # Try to get from environment
            env_keys = {
                LLMProvider.KIMI: "KIMI_API_KEY",
                LLMProvider.OPENAI: "OPENAI_API_KEY",
                LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            }
            self.api_key = os.getenv(env_keys.get(self.provider, "KIMI_API_KEY"))

        if self.base_url is None:
            # Default base URLs
            urls = {
                LLMProvider.KIMI: "https://api.moonshot.cn/v1",
                LLMProvider.OPENAI: "https://api.openai.com/v1",
                LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1",
            }
            self.base_url = urls.get(self.provider, "https://api.moonshot.cn/v1")


@dataclass
class Message:
    """A chat message."""
    role: str  # system, user, assistant
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = None
    raw_response: Dict = None


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Usage:
        client = LLMClient.from_kimi("your-api-key")
        response = client.chat("Generate a placement for...")
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    @classmethod
    def from_kimi(cls, api_key: str, model: str = "moonshot-v1-8k") -> "LLMClient":
        """Create a Kimi client."""
        config = LLMConfig(
            provider=LLMProvider.KIMI,
            api_key=api_key,
            model=model,
            base_url="https://api.moonshot.cn/v1"
        )
        return cls(config)

    @classmethod
    def from_openai(cls, api_key: str, model: str = "gpt-4") -> "LLMClient":
        """Create an OpenAI client."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key=api_key,
            model=model,
            base_url="https://api.openai.com/v1"
        )
        return cls(config)

    @classmethod
    def from_anthropic(cls, api_key: str, model: str = "claude-3-sonnet-20240229") -> "LLMClient":
        """Create an Anthropic client."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key=api_key,
            model=model,
            base_url="https://api.anthropic.com/v1"
        )
        return cls(config)

    def chat(self, prompt: str, system_prompt: str = None,
             temperature: float = None, max_tokens: int = None) -> LLMResponse:
        """
        Send a single chat message.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            LLMResponse with generated content
        """
        messages = []
        if system_prompt:
            messages.append(Message("system", system_prompt))
        messages.append(Message("user", prompt))

        return self.chat_messages(messages, temperature, max_tokens)

    def chat_messages(self, messages: List[Message],
                      temperature: float = None,
                      max_tokens: int = None) -> LLMResponse:
        """
        Send multiple messages (for conversation context).

        Args:
            messages: List of Message objects
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            LLMResponse
        """
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        # Prepare request based on provider
        if self.config.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(messages, temp, tokens)
        else:
            # OpenAI-compatible (Kimi, OpenAI)
            return self._call_openai_compatible(messages, temp, tokens)

    def _call_openai_compatible(self, messages: List[Message],
                                temperature: float,
                                max_tokens: int) -> LLMResponse:
        """Call OpenAI-compatible API (Kimi, OpenAI)."""
        url = f"{self.config.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Retry logic
        for attempt in range(self.config.retry_count):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data.get("model", self.config.model),
                    usage=data.get("usage", {}),
                    finish_reason=data["choices"][0].get("finish_reason"),
                    raw_response=data
                )

            except requests.exceptions.RequestException as e:
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                raise LLMError(f"API call failed after {self.config.retry_count} attempts: {e}")

    def _call_anthropic(self, messages: List[Message],
                        temperature: float,
                        max_tokens: int) -> LLMResponse:
        """Call Anthropic API (Claude)."""
        url = f"{self.config.base_url}/messages"

        # Separate system message
        system_message = None
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_message = m.content
            else:
                chat_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": self.config.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if system_message:
            payload["system"] = system_message

        # Anthropic uses x-api-key header
        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        for attempt in range(self.config.retry_count):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data["content"][0]["text"],
                    model=data.get("model", self.config.model),
                    usage={
                        "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("output_tokens", 0)
                    },
                    finish_reason=data.get("stop_reason"),
                    raw_response=data
                )

            except requests.exceptions.RequestException as e:
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                raise LLMError(f"API call failed after {self.config.retry_count} attempts: {e}")

    def stream_chat(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        """
        Stream chat response (for interactive use).

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Yields:
            Chunks of generated text
        """
        messages = []
        if system_prompt:
            messages.append(Message("system", system_prompt))
        messages.append(Message("user", prompt))

        url = f"{self.config.base_url}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True
        }

        response = self.session.post(url, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue


class LLMError(Exception):
    """LLM API error."""
    pass


# Convenience functions
def get_default_client() -> LLMClient:
    """Get default client from environment variables."""
    # Try Kimi first, then OpenAI, then Anthropic
    if os.getenv("KIMI_API_KEY"):
        return LLMClient.from_kimi(os.getenv("KIMI_API_KEY"))
    elif os.getenv("OPENAI_API_KEY"):
        return LLMClient.from_openai(os.getenv("OPENAI_API_KEY"))
    elif os.getenv("ANTHROPIC_API_KEY"):
        return LLMClient.from_anthropic(os.getenv("ANTHROPIC_API_KEY"))
    else:
        raise LLMError("No API key found. Set KIMI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY.")


def quick_chat(prompt: str, api_key: str = None, provider: str = "kimi") -> str:
    """
    Quick one-off chat without creating a client.

    Args:
        prompt: User prompt
        api_key: API key (if not set in environment)
        provider: Provider name (kimi, openai, anthropic)

    Returns:
        Generated text
    """
    if api_key:
        os.environ[f"{provider.upper()}_API_KEY"] = api_key

    client = get_default_client()
    response = client.chat(prompt)
    return response.content


if __name__ == "__main__":
    # Test the client
    print("Testing LLM Client...")

    # Try to use environment variable
    try:
        client = get_default_client()
        print(f"Using provider: {client.config.provider.value}")
        print(f"Model: {client.config.model}")

        # Quick test
        response = client.chat("Hello! Please respond with 'LLM Client is working.'")
        print(f"\nResponse: {response.content}")
        print(f"Usage: {response.usage}")

    except LLMError as e:
        print(f"Error: {e}")
        print("\nTo test, set one of these environment variables:")
        print("  - KIMI_API_KEY")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY")
