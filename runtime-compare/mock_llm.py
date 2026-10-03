#!/usr/bin/env python3
"""Deterministic OpenAI-compatible mock of the vLLM backend.

Lets the comparison run without a GPU and isolates framework overhead:
every request is recorded so we can count LLM calls and prompt size.
"""

import os
import asyncio
import time
import uuid

from fastapi import FastAPI, Request

app = FastAPI(title="Mock vLLM")
LATENCY_S = float(os.getenv("MOCK_LATENCY_MS", "0")) / 1000
CALLS: list[dict] = []

LEGAL_WORDS = ("licens", "legal", "gpl", "commercial", "compliance", "copyright")

ARCHITECT_REPLY = """1. Architecture Options: event-driven microservices; modular monolith.
2. Recommended Open Source Technologies: Apache Kafka, PostgreSQL, Kubernetes, Redis.
3. Complexity Assessment: Medium
4. Estimated Timeline: 10-14 weeks
5. Key Technical Considerations: idempotent consumers, schema evolution, observability."""

LAWYER_REPLY = """Apache Kafka - Apache 2.0 - Commercial: Yes - Keep NOTICE file - Risk: Low
PostgreSQL - PostgreSQL License - Commercial: Yes - Keep copyright notice - Risk: Low
Kubernetes - Apache 2.0 - Commercial: Yes - Keep NOTICE file - Risk: Low
Redis - RSALv2/SSPLv1 (7.4+) - Commercial: Yes, unless offered as a managed service - Risk: Medium"""


def _text(content) -> str:
    if isinstance(content, list):
        return " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def _reply(messages: list[dict]) -> str:
    system = " ".join(_text(m.get("content")) for m in messages if m.get("role") == "system")
    user = " ".join(_text(m.get("content")) for m in messages if m.get("role") == "user")
    if "AI Coordinator" in system:
        return "LAWYER" if any(w in user.lower() for w in LEGAL_WORDS) else "ARCHITECT"
    if "License Attorney" in system:
        return LAWYER_REPLY
    return ARCHITECT_REPLY


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    content = _reply(messages)
    prompt_chars = sum(len(_text(m.get("content"))) for m in messages)
    CALLS.append({"messages": len(messages), "prompt_chars": prompt_chars, "body": body})
    if LATENCY_S:
        await asyncio.sleep(LATENCY_S)
    # ~4 chars per token is close enough for a relative comparison
    prompt_tokens, completion_tokens = prompt_chars // 4, len(content) // 4
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "mock"),
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                  "total_tokens": prompt_tokens + completion_tokens},
    }


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [{"id": os.getenv("MODEL_NAME", "mock"), "object": "model"}]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
