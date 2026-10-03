"""Shared config for the AgentOS vs CrewAI comparison.

Both implementations reuse the system prompts from the root app.py so the
only variable being compared is the framework.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import AGENT_PROMPTS  # noqa: E402

# OpenAI-compatible endpoint: vLLM in the real deployment, mock_llm.py locally.
# Note: base URL, not the full /chat/completions path that app.py uses.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "microsoft/Phi-3-mini-4k-instruct")
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")

# Keep both frameworks from phoning home during benchmarks.
os.environ.setdefault("AGNO_TELEMETRY", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


def parse_route(text: str) -> str:
    """Same routing rule as app.route_query: default to architect."""
    return "lawyer" if "LAWYER" in text.upper() and "ARCHITECT" not in text.upper() else "architect"
