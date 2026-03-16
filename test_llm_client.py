"""Test LLM Client with working Kimi API Key."""

import sys
sys.path.insert(0, 'src')

from llm.client import LLMClient

# Working Kimi API Key
API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"

print("=" * 60)
print("Testing LLM Client with Kimi API")
print("=" * 60)

# Create client
client = LLMClient.from_kimi(API_KEY)

print(f"\nProvider: {client.config.provider.value}")
print(f"Base URL: {client.config.base_url}")
print(f"Model: {client.config.model}")
print(f"API Key: {API_KEY[:20]}...{API_KEY[-4:]}")

# Test 1: Simple chat
print("\n" + "-" * 60)
print("Test 1: Simple Chat")
print("-" * 60)

try:
    response = client.chat(
        prompt="Hello! Please say 'Kimi API is working!' and explain what a digital microfluidic biochip is in one sentence.",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=150
    )

    print(f"\n[OK] Success!")
    print(f"\nResponse:\n{response.content}")
    print(f"\nUsage: {response.usage}")
    print(f"Finish reason: {response.finish_reason}")

except Exception as e:
    print(f"\n[FAIL] {type(e).__name__}: {e}")

# Test 2: Placement-related prompt
print("\n" + "-" * 60)
print("Test 2: DMFB Placement Prompt")
print("-" * 60)

try:
    placement_prompt = """You are a DMFB (Digital Microfluidic Biochip) placement optimizer.

Given a problem with:
- Chip size: 20x20
- Operations: 5 mix operations
- Dependencies: mix_0 -> mix_1, mix_0 -> mix_2

Generate a valid placement (x, y coordinates) for each module.
Ensure no overlapping modules and all modules within chip boundaries.

Return the result as JSON format:
{
  "placements": [
    {"operation_id": 0, "module_type": "mixer_2x2", "x": 0, "y": 0},
    ...
  ]
}"""

    response = client.chat(
        prompt=placement_prompt,
        system_prompt="You are an expert in DMFB design automation.",
        temperature=0.3,
        max_tokens=500
    )

    print(f"\n[OK] Placement prompt success!")
    print(f"\nResponse preview (first 500 chars):\n{response.content[:500]}...")

except Exception as e:
    print(f"\n[FAIL] {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("LLM Client test complete!")
print("=" * 60)
