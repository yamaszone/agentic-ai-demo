# Agent runtime prototype: AgentOS vs CrewAI

This prototype builds the root demo (`../app.py`) twice: once on
[Agno AgentOS](https://docs.agno.com) and once on [CrewAI](https://docs.crewai.com).
Both versions use the same system prompts (imported from `app.py`) and the same
OpenAI-compatible backend, so the only thing that changes between them is the framework.

| File | Purpose |
|---|---|
| `agentos_app.py` | Agents and workflows on Agno. AgentOS generates the whole HTTP service. |
| `crewai_app.py` | Agents on CrewAI: a `Flow` for routing and a sequential `Crew` for the pipeline, behind a hand-written FastAPI wrapper. |
| `mock_llm.py` | Deterministic OpenAI-compatible stand-in for vLLM. It records every call it receives. |
| `compare.py` | Benchmark harness. It calls both services over HTTP and writes `results.md`. |
| `common.py` | Shared config (`LLM_BASE_URL`, `MODEL_NAME`) and the shared prompts. |

## Scenarios

1. **Route**: the same flow as `app.py` with `agent="auto"`. The coordinator classifies
   the query, then the architect or the lawyer answers it.
   - Agno: `Workflow` = `Step(coordinator)` → `Router(architect | lawyer)`
   - CrewAI: `Flow` with `@start` classify → `@router` → `@listen("architect"|"lawyer")`
2. **Pipeline**: the architect designs a system, then the lawyer reviews the licenses of
   the technologies the architect chose (the "Full Software Project Analysis" scenario
   from the root README).
   - Agno: a two-step `Workflow`
   - CrewAI: a `Crew` with `Process.sequential` and `context=[design_task]`

Neither scenario uses tool calling, so both also run against Phi-3 on vLLM.

## Run it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r runtime-compare/requirements.txt
cd runtime-compare

python compare.py                          # framework overhead only (mock, 0 ms)
MOCK_LATENCY_MS=300 python compare.py      # simulate a slower GPU backend
LLM_BASE_URL=http://localhost:8000/v1 python compare.py   # real vLLM (port-forward)

# Serve either one
python agentos_app.py   # http://localhost:8080/docs  e.g. POST /workflows/route/runs
python crewai_app.py    # http://localhost:8081/docs  POST /query, POST /pipeline
```

## Results (mock backend, 0 ms per call, 5 runs per query)

| Metric | AgentOS (Agno 3.1.1) | CrewAI 1.15.23 |
|---|---|---|
| Cold start: import + build (s) | 2.30 | 2.87 |
| Implementation size (code lines) | 49 | 72 |
| HTTP API paths (OpenAPI) | 93 | 3 |
| Route: p50 latency (ms) | 23 | 48 |
| Route: prompt chars / request | 902 | 1246 |
| Pipeline: p50 latency (ms) | 17 | 40 |
| Pipeline: prompt chars / request | 1300 | 2065 |
| LLM calls / request (both scenarios) | 2.0 | 2.0 |
| Failed checks | 0/25 | 0/25 |

With a 300 ms mock latency per call, both runtimes land at about 0.63–0.67 s per request.
At that point the LLM dominates, and the gap between the frameworks (about 25–40 ms) is
small. The `results.md` file has the full output of the latest run.

## Findings

**AgentOS (Agno)**
- **Runtime included:** `AgentOS(...).get_app()` produces a FastAPI app with 93 API paths:
  runs, sessions, memory, metrics, evals, an MCP server option, and auth/RBAC hooks.
  Sessions are persisted to SQLite (or Postgres) automatically. That's why the
  implementation is the smallest of the two.
- **Leaner prompts:** `instructions` are passed through almost unchanged, so the prompt is
  about 30–40% smaller. That matters for Phi-3's 4k context.
- **Less context in the pipeline:** the lawyer step receives only the architect's output,
  not the original query.
- **Noisy logs:** version 3.1.1 logs `WorkflowSession not persisted (ownership mismatch)`
  on every workflow run. Workflow sessions are still persisted (`GET /sessions?type=workflow`
  lists them), so it is only log noise.

**CrewAI**
- **No serving layer:** CrewAI is an orchestration library. The FastAPI endpoints,
  persistence, and auth have to be written by hand (or you use the paid CrewAI AMP platform).
- **Richer orchestration:** `Flow` (event-driven state machine) and `Crew` (role/goal/task
  with context passing) are expressive. The lawyer task gets the task description, the
  expected output, and the architect's design as context.
- **Bigger prompts:** each prompt is wrapped in a role/goal/task template ("You are {role}…
  Your personal goal is…"), which adds tokens to every call and roughly doubles the
  per-request overhead.
- **Console output:** `Flow` prints Rich panels on every step regardless of `verbose`. They
  are silenced here with `set_suppress_console_output(True)`.

**Choosing between them**
- **Pick AgentOS** for this demo's use case: a containerized service on GKE in front of a
  small-context model. You get the API, persistence, and observability built in, plus
  smaller prompts.
- **Pick CrewAI** when the value is in multi-step, role-based collaboration (for example,
  delegation or hierarchical crews) and you already have, or want to own, the service layer.

## Caveats

- **Latency numbers:** these come from the mock backend and only measure framework
  overhead. Answer quality is not measured.
- **Token counts:** the mock returns canned answers and estimates tokens at 4 chars each.
- **Version churn:** both frameworks change quickly. The numbers above are for the pinned
  versions in `requirements.txt`.
