#!/usr/bin/env python3
"""
Multi-Agent AI Demo - Minimalist Implementation
Demonstrates GPU-accelerated Agentic AI using prompt engineering
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from typing import Literal

app = FastAPI(title="Multi-Agent AI Demo", version="1.0.0")

# vLLM inference endpoint (can be local or remote)
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "microsoft/Phi-3-mini-4k-instruct")

# Agent system prompts
AGENT_PROMPTS = {
    "architect": """You are an experienced Software Architect with 15+ years of experience.
Your role is to analyze software engineering problems and provide architectural solutions.

For each request, provide:
1. Architecture Options (2-3 options)
2. Recommended Open Source Technologies
3. Complexity Assessment (Low/Medium/High)
4. Estimated Timeline (in weeks)
5. Key Technical Considerations

Be concise but thorough. Focus on practical, production-ready solutions.""",

    "lawyer": """You are an Open Source License Attorney specializing in software licensing.
Your role is to analyze open source technologies for legal compliance and commercial use.

For each technology mentioned, provide:
1. License Type (MIT, Apache 2.0, GPL, etc.)
2. Commercial Permissibility (Yes/No with conditions)
3. Key License Restrictions
4. Compliance Requirements
5. Risk Assessment (Low/Medium/High)

Be precise and focus on practical legal implications for commercial use.""",

    "coordinator": """You are an AI Coordinator that routes requests to specialized agents.
Analyze the user's query and determine which agent should handle it:

- ARCHITECT: Software design, architecture, technology choices, implementation planning
- LAWYER: Licensing, legal compliance, open source usage rights, commercial permissions

Respond with ONLY the agent name: ARCHITECT or LAWYER"""
}


class AgentRequest(BaseModel):
    query: str
    agent: Literal["architect", "lawyer", "auto"] = "auto"


class AgentResponse(BaseModel):
    agent: str
    query: str
    response: str


async def call_llm(system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
    """Call vLLM inference endpoint"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": temperature,
        "max_tokens": 1024
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(INFERENCE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"LLM inference error: {str(e)}")


async def route_query(query: str) -> str:
    """Use coordinator to determine which agent should handle the query"""
    response = await call_llm(AGENT_PROMPTS["coordinator"], query, temperature=0.3)

    # Parse coordinator response
    agent = response.strip().upper()
    if "ARCHITECT" in agent:
        return "architect"
    elif "LAWYER" in agent:
        return "lawyer"
    else:
        # Default to architect if unclear
        return "architect"


@app.get("/")
async def root():
    return {
        "service": "Multi-Agent AI Demo",
        "agents": ["architect", "lawyer", "coordinator"],
        "endpoints": {
            "query": "/query",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "inference_url": INFERENCE_URL}


@app.post("/query", response_model=AgentResponse)
async def query_agent(request: AgentRequest):
    """
    Query an agent with automatic routing

    - agent="auto": Coordinator determines the appropriate agent
    - agent="architect": Direct query to architect agent
    - agent="lawyer": Direct query to lawyer agent
    """

    # Determine which agent to use
    if request.agent == "auto":
        selected_agent = await route_query(request.query)
    else:
        selected_agent = request.agent

    # Get response from selected agent
    system_prompt = AGENT_PROMPTS[selected_agent]
    response = await call_llm(system_prompt, request.query)

    return AgentResponse(
        agent=selected_agent,
        query=request.query,
        response=response
    )


@app.get("/agents")
async def list_agents():
    """List available agents and their capabilities"""
    return {
        "agents": {
            "architect": {
                "description": "Software architecture and technology recommendations",
                "capabilities": [
                    "Architecture design",
                    "Technology selection",
                    "Complexity assessment",
                    "Timeline estimation"
                ]
            },
            "lawyer": {
                "description": "Open source licensing and legal compliance",
                "capabilities": [
                    "License analysis",
                    "Commercial permissibility",
                    "Risk assessment",
                    "Compliance guidance"
                ]
            },
            "coordinator": {
                "description": "Automatic agent routing",
                "capabilities": [
                    "Query classification",
                    "Agent selection",
                    "Request routing"
                ]
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
