# AgentOS vs CrewAI - benchmark results

Backend: mock_llm.py, latency 0 ms/call · runs per query: 5 · Python 3.11.15

| Metric | AgentOS (Agno) | CrewAI |
|---|---|---|
| Cold start: import + build (s) | 2.30 | 2.87 |
| Implementation size (code lines) | 49 | 72 |
| HTTP API paths (OpenAPI) | 93 | 3 |
| Route: p50 latency (ms) | 23 | 48 |
| Route: mean latency (ms) | 26 | 50 |
| Route: LLM calls / request | 2.0 | 2.0 |
| Route: prompt chars / request | 902 | 1246 |
| Route: failed checks | 0/20 | 0/20 |
| Pipeline: p50 latency (ms) | 17 | 40 |
| Pipeline: mean latency (ms) | 17 | 46 |
| Pipeline: LLM calls / request | 2.0 | 2.0 |
| Pipeline: prompt chars / request | 1300 | 2065 |
| Pipeline: failed checks | 0/5 | 0/5 |
