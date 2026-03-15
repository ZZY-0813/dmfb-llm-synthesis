"""
Mock LLM Client for testing without API access.

Simulates LLM responses for development and testing.
"""

import json
import random
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, 'src')
try:
    from llm.client import LLMResponse, Message
except ImportError:
    # Fallback for direct execution
    from client import LLMResponse, Message


class MockLLMClient:
    """
    Mock LLM client that returns predefined responses.

    Modes:
    - "success": Always return valid solutions
    - "error": Always return invalid solutions (for testing repair)
    - "random": Randomly succeed or fail
    - "placement_error": Return placement with overlap error
    - "schedule_error": Return schedule with dependency error
    """

    def __init__(self, mode: str = "success", seed: int = 42):
        """
        Initialize mock client.

        Args:
            mode: "success", "error", "random", "placement_error", "schedule_error"
            seed: Random seed for reproducibility
        """
        self.mode = mode
        self.seed = seed
        random.seed(seed)
        self.call_count = 0

    @classmethod
    def from_kimi(cls, api_key: str = None, mode: str = "success"):
        """Factory method matching LLMClient interface."""
        return cls(mode=mode)

    def chat(self, prompt: str, system_prompt: str = None,
             temperature: float = None, max_tokens: int = None) -> LLMResponse:
        """
        Simulate chat response.

        Analyzes prompt to determine what type of solution to return.
        """
        self.call_count += 1

        # Determine what type of solution is being requested
        if "placement" in prompt.lower() or "布局" in prompt:
            content = self._generate_placement_response(prompt)
        elif "schedule" in prompt.lower() or "调度" in prompt:
            content = self._generate_schedule_response(prompt)
        elif "routing" in prompt.lower() or "路由" in prompt:
            content = self._generate_routing_response(prompt)
        else:
            content = self._generate_generic_response()

        return LLMResponse(
            content=content,
            model="mock-moonshot-v1-8k",
            usage={
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split())
            },
            finish_reason="stop"
        )

    def chat_messages(self, messages: List[Message], **kwargs) -> LLMResponse:
        """Simulate chat with message history."""
        prompt = "\n".join([m.content for m in messages])
        return self.chat(prompt, **kwargs)

    def _generate_placement_response(self, prompt: str) -> str:
        """Generate mock placement solution."""
        if self.mode == "error" or (self.mode == "random" and random.random() < 0.3):
            # Return invalid placement (overlapping modules)
            return """I'll place the modules with some overlap to test error handling.

```json
[
  {"module_id": "mixer_0", "x": 2, "y": 2, "width": 3, "height": 3},
  {"module_id": "heater_0", "x": 3, "y": 3, "width": 2, "height": 2}
]
```
"""
        elif self.mode == "placement_error":
            # Return out of bounds
            return """Placing modules at edges.

```json
[
  {"module_id": "mixer_0", "x": 8, "y": 8, "width": 3, "height": 3}
]
```
"""
        else:
            # Return valid placement
            return """Based on the problem requirements, I'll place modules with adequate spacing:

```json
[
  {"module_id": "mixer_0", "x": 2, "y": 2, "width": 2, "height": 2},
  {"module_id": "heater_0", "x": 5, "y": 2, "width": 1, "height": 1},
  {"module_id": "detector_0", "x": 2, "y": 5, "width": 1, "height": 2}
]
```

The mixer is placed at (2,2) to leave room for droplet routing. The heater and detector are positioned nearby to minimize routing distance for sequential operations.
"""

    def _generate_schedule_response(self, prompt: str) -> str:
        """Generate mock schedule solution."""
        if self.mode == "error" or (self.mode == "random" and random.random() < 0.3):
            # Return invalid schedule (dependency violation)
            return """Scheduling operations to minimize makespan.

```json
[
  {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_2x2"},
  {"operation_id": 1, "start_time": 1, "end_time": 4, "module_id": "heater_1x1"}
]
```
"""
        elif self.mode == "schedule_error":
            # Return resource conflict
            return """Scheduling with potential overlap.

```json
[
  {"operation_id": 0, "start_time": 0, "end_time": 5, "module_id": "mixer_2x2"},
  {"operation_id": 1, "start_time": 3, "end_time": 8, "module_id": "mixer_2x2"}
]
```
"""
        else:
            # Return valid schedule
            return """Analyzing the dependency graph, I identify:
- Critical path: Op 0 → Op 1
- Op 0 has no dependencies, can start at t=0
- Op 1 depends on Op 0, must start after t=3

```json
[
  {"operation_id": 0, "start_time": 0, "end_time": 3, "module_id": "mixer_2x2"},
  {"operation_id": 1, "start_time": 3, "end_time": 7, "module_id": "heater_1x1"}
]
```

Makespan: 7 ticks
"""

    def _generate_routing_response(self, prompt: str) -> str:
        """Generate mock routing solution."""
        if self.mode == "error" or (self.mode == "random" and random.random() < 0.3):
            # Return collision path
            return """Routing droplets with direct paths.

```json
[
  {"droplet_id": "d0", "path": [[0, 1, 1], [1, 2, 1], [2, 3, 1]]},
  {"droplet_id": "d1", "path": [[0, 3, 3], [1, 2, 1], [2, 1, 1]]}
]
```
"""
        else:
            # Return valid routes
            return """Planning collision-free paths:

```json
[
  {"droplet_id": "d0", "path": [[0, 1, 1], [1, 2, 1], [2, 3, 1]]},
  {"droplet_id": "d1", "path": [[0, 5, 5], [1, 5, 6], [2, 5, 7]]}
]
```

Droplets are routed on separate paths to avoid collisions.
"""

    def _generate_generic_response(self) -> str:
        """Generate generic response."""
        return """This is a mock response from the MockLLMClient.

```json
{"status": "mock", "message": "API not available, using mock mode"}
```
"""


def test_mock_client():
    """Test the mock client."""
    print("Testing MockLLMClient...")

    # Test success mode
    client = MockLLMClient(mode="success")
    response = client.chat("Generate a placement for...")
    print(f"\n[Success Mode]")
    print(f"Response length: {len(response.content)}")
    print(f"Usage: {response.usage}")

    # Test error mode
    client = MockLLMClient(mode="error")
    response = client.chat("Generate a placement for...")
    print(f"\n[Error Mode]")
    print(f"Response (first 200 chars): {response.content[:200]}...")

    # Test placement with error
    client = MockLLMClient(mode="placement_error")
    response = client.chat("Generate a placement for...")
    print(f"\n[Placement Error Mode]")
    check = '"x": 8' in response.content
    print(f"Contains 'out of bounds' placement: {check}")

    print("\nMock client tests passed!")


if __name__ == "__main__":
    test_mock_client()
