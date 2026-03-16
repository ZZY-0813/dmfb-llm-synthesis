"""Test API key to identify provider."""

import requests
import sys

API_KEY = "sk-SEd9538RQoEuFkuvotMWQRd0hHkuGxfnrQfAuwVMMh86pm7y"

def test_openai():
    """Test if it's OpenAI."""
    print("Testing OpenAI API...")
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            },
            timeout=10
        )
        if response.status_code == 200:
            print("[OK] OpenAI API works!")
            return True
        else:
            print(f"[FAIL] OpenAI: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] OpenAI: {e}")
        return False

def test_kimi():
    """Test if it's Kimi (Moonshot)."""
    print("\nTesting Kimi (Moonshot) API...")
    try:
        response = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "moonshot-v1-8k",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            },
            timeout=10
        )
        if response.status_code == 200:
            print("[OK] Kimi API works!")
            return True
        else:
            print(f"[FAIL] Kimi: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Kimi: {e}")
        return False

def test_anthropic():
    """Test if it's Anthropic (Claude)."""
    print("\nTesting Anthropic (Claude) API...")
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            },
            timeout=10
        )
        if response.status_code == 200:
            print("[OK] Anthropic API works!")
            return True
        else:
            print(f"[FAIL] Anthropic: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Anthropic: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("API Key Testing")
    print("=" * 60)
    print(f"Key: {API_KEY[:20]}...{API_KEY[-4:]}")
    print()

    # Test all providers
    openai_works = test_openai()
    kimi_works = test_kimi()
    anthropic_works = test_anthropic()

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  OpenAI:    {'✓' if openai_works else '✗'}")
    print(f"  Kimi:      {'✓' if kimi_works else '✗'}")
    print(f"  Anthropic: {'✓' if anthropic_works else '✗'}")
    print("=" * 60)
