"""
LLM module for DMFB synthesis.

Provides unified interface to multiple LLM providers.
"""

from .client import (
    LLMClient,
    LLMConfig,
    LLMResponse,
    Message,
    LLMProvider,
    LLMError,
    get_default_client,
    quick_chat
)

from .mock_client import MockLLMClient

__all__ = [
    'LLMClient',
    'LLMConfig',
    'LLMResponse',
    'Message',
    'LLMProvider',
    'LLMError',
    'get_default_client',
    'quick_chat',
    'MockLLMClient',
]
