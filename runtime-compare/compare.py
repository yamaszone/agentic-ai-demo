#!/usr/bin/env python3
"""Benchmark the AgentOS and CrewAI implementations side by side.

Starts mock_llm.py in-process (unless LLM_BASE_URL points elsewhere), drives
both services through their HTTP APIs and prints a markdown report.

    python compare.py                    # framework overhead only
    MOCK_LATENCY_MS=500 python compare.py  # simulate a slow GPU backend
    LLM_BASE_URL=http://localhost:8000/v1 python compare.py  # real vLLM
"""

import argparse
import os
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).parent
MOCK_PORT = 8765
USE_MOCK = "LLM_BASE_URL" not in os.environ
if USE_MOCK:
    os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{MOCK_PORT}/v1"

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import mock_llm  # noqa: E402

# (query, expected agent) - taken from the root README / test-local.sh
ROUTE_QUERIES = [
    ("Design a real-time data pipeline for IoT sensors", "architect"),
    ("What technology stack would you recommend for a microservices platform?", "architect"),
    ("Is GPL-licensed software compatible with proprietary software?", "lawyer"),
    ("What are the licensing requirements for Apache Kafka in a commercial product?", "lawyer"),
]
PIPELINE_QUERY = "Design a video streaming platform with CDN, transcoding and storage"


def start_mock():
    server = uvicorn.Server(uvicorn.Config(mock_llm.app, port=MOCK_PORT, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        try:
            httpx.get(f"http://127.0.0.1:{MOCK_PORT}/v1/models")
            return
        except httpx.HTTPError:
            time.sleep(0.1)
    sys.exit("mock LLM did not start")


def cold_start_seconds(module: str) -> float:
    """Fresh interpreter: import framework + build agents/app."""
    code = f"import time; t=time.perf_counter(); import {module}; print(time.perf_counter()-t)"
    out = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True,
                         text=True, env=os.environ, check=True)
    return float(out.stdout.strip().splitlines()[-1])


def code_lines(path: Path) -> int:
    lines = [ln.strip() for ln in path.read_text().splitlines()]
    in_doc, count = False, 0
    for ln in lines:
        if ln.startswith('"""'):
            in_doc = not in_doc if ln.count('"""') == 1 else in_doc
            continue
        if not in_doc and ln and not ln.startswith("#"):
            count += 1
    return count


# Each adapter returns (agent_that_answered, answer_text)
def agentos_route(client, query):
    r = client.post("/workflows/route/runs", data={"message": query, "stream": "false"})
    r.raise_for_status()
    body = r.json()
    agent = "lawyer" if "lawyer" in body["metrics"]["steps"] else "architect"
    return agent, body["content"]


def agentos_pipeline(client, query):
    r = client.post("/workflows/pipeline/runs", data={"message": query, "stream": "false"})
    r.raise_for_status()
    return "pipeline", r.json()["content"]


def crewai_route(client, query):
    r = client.post("/query", json={"query": query, "agent": "auto"})
    r.raise_for_status()
    return r.json()["agent"], r.json()["response"]


def crewai_pipeline(client, query):
    r = client.post("/pipeline", json={"query": query})
    r.raise_for_status()
    return "pipeline", r.json()["lawyer"]


def bench(client, fn, queries, runs):
    latencies, calls, chars, wrong = [], [], [], 0
    for _ in range(runs):
        for query, expected in queries:
            before = len(mock_llm.CALLS)
            t = time.perf_counter()
            agent, answer = fn(client, query)
            latencies.append(time.perf_counter() - t)
            new = mock_llm.CALLS[before:]
            calls.append(len(new))
            chars.append(sum(c["prompt_chars"] for c in new))
            if expected is None:  # pipeline: lawyer must see the architect's design
                handoff = str(new[-1]["body"]["messages"]) if new else ""
                wrong += USE_MOCK and "Apache Kafka, PostgreSQL" not in handoff
            wrong += (expected is not None and agent != expected) or not answer
    return {
        "p50_ms": statistics.median(latencies) * 1000,
        "mean_ms": statistics.mean(latencies) * 1000,
        "llm_calls": statistics.mean(calls) if USE_MOCK else None,
        "prompt_chars": statistics.mean(chars) if USE_MOCK else None,
        "errors": wrong,
        "n": len(latencies),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5, help="repetitions per query")
    parser.add_argument("--out", default=str(HERE / "results.md"))
    args = parser.parse_args()

    if USE_MOCK:
        start_mock()
    (HERE / "tmp").mkdir(exist_ok=True)

    os.chdir(HERE)
    import agentos_app
    import crewai_app

    impls = {
        "AgentOS (Agno)": (agentos_app, agentos_route, agentos_pipeline),
        "CrewAI": (crewai_app, crewai_route, crewai_pipeline),
    }
    rows = []
    for name, (module, route_fn, pipe_fn) in impls.items():
        with TestClient(module.app) as client:
            route_fn(client, ROUTE_QUERIES[0][0])  # warm-up
            route = bench(client, route_fn, ROUTE_QUERIES, args.runs)
            pipe = bench(client, pipe_fn, [(PIPELINE_QUERY, None)], args.runs)
            n_routes = len(client.get("/openapi.json").json()["paths"])
        rows.append((name, module, route, pipe, n_routes))

    def fmt(v, spec=".0f"):
        return "n/a" if v is None else format(v, spec)

    latency = os.getenv("MOCK_LATENCY_MS", "0") if USE_MOCK else "real backend"
    out = [
        "# AgentOS vs CrewAI - benchmark results",
        "",
        f"Backend: {'mock_llm.py, latency ' + latency + ' ms/call' if USE_MOCK else os.environ['LLM_BASE_URL']}"
        f" · runs per query: {args.runs} · Python {sys.version.split()[0]}",
        "",
        "| Metric | " + " | ".join(r[0] for r in rows) + " |",
        "|---|" + "---|" * len(rows),
    ]

    def row(label, values):
        out.append(f"| {label} | " + " | ".join(values) + " |")

    row("Cold start: import + build (s)", [f"{cold_start_seconds(r[1].__name__):.2f}" for r in rows])
    row("Implementation size (code lines)", [str(code_lines(Path(r[1].__file__))) for r in rows])
    row("HTTP API paths (OpenAPI)", [str(r[4]) for r in rows])
    for label, idx in (("Route", 2), ("Pipeline", 3)):
        row(f"{label}: p50 latency (ms)", [fmt(r[idx]["p50_ms"]) for r in rows])
        row(f"{label}: mean latency (ms)", [fmt(r[idx]["mean_ms"]) for r in rows])
        row(f"{label}: LLM calls / request", [fmt(r[idx]["llm_calls"], ".1f") for r in rows])
        row(f"{label}: prompt chars / request", [fmt(r[idx]["prompt_chars"]) for r in rows])
        row(f"{label}: failed checks", [f"{r[idx]['errors']}/{r[idx]['n']}" for r in rows])

    report = "\n".join(out) + "\n"
    print(report)
    Path(args.out).write_text(report)


if __name__ == "__main__":
    main()
