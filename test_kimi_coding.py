"""Test Kimi For Coding API."""

import sys
sys.path.insert(0, 'src')

from llm.client import LLMClient

# Your Kimi For Coding API Key
API_KEY = "sk-kimi-z1IYhREbJ7t20S9yRkyavdsE7f0vHtNsqNyqm4wfAvYEnNASt5HZ4LYmXh4bGRRm"

print("=" * 60)
print("Testing Kimi For Coding API")
print("=" * 60)

# Create client with Kimi For Coding endpoint
client = LLMClient.from_kimi_coding(API_KEY)

print(f"\nAPI Endpoint: {client.config.base_url}")
print(f"Model: {client.config.model}")
print(f"API Key: {API_KEY[:20]}...{API_KEY[-4:]}")

# Test connection
try:
    print("\n" + "-" * 60)
    print("Sending test message...")
    print("-" * 60)

    response = client.chat(
        prompt="Hello! This is a test from DMFB project. Please respond with 'Kimi API is working!' and explain what a digital microfluidic biochip is in one sentence.",
        system_prompt="You are a helpful assistant for a biochip design project.",
        temperature=0.7,
        max_tokens=200
    )

    print(f"\n[OK] API Connection Successful!")
    print(f"\nResponse:\n{response.content}")
    print(f"\nModel used: {response.model}")
    print(f"Token usage: {response.usage}")
    print(f"Finish reason: {response.finish_reason}")

except Exception as e:
    print(f"\n[FAIL] API Connection Failed:")
    print(f"  Error type: {type(e).__name__}")
    print(f"  Error message: {e}")

    # Try to get more details
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
