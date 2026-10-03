#!/usr/bin/env python3
"""The demo's coordinator/architect/lawyer agents on Agno AgentOS.

AgentOS generates the FastAPI service itself (runs, sessions, health,
OpenAPI docs), so this file only declares agents and workflows.

Run:  python agentos_app.py   ->  http://localhost:8080/docs
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai.like import OpenAILike
from agno.os import AgentOS
from agno.workflow import Router, Step, StepInput, Workflow

from common import AGENT_PROMPTS, LLM_API_KEY, LLM_BASE_URL, MODEL_NAME, parse_route


def _model() -> OpenAILike:
    return OpenAILike(id=MODEL_NAME, base_url=LLM_BASE_URL, api_key=LLM_API_KEY,
                      max_tokens=1024)


def _agent(name: str, temperature: float = 0.7) -> Agent:
    model = _model()
    model.temperature = temperature
    return Agent(id=name, name=name.title(), model=model, instructions=AGENT_PROMPTS[name],
                 telemetry=False)


coordinator = _agent("coordinator", temperature=0.3)
architect = _agent("architect")
lawyer = _agent("lawyer")

architect_step = Step(name="architect", agent=architect)
lawyer_step = Step(name="lawyer", agent=lawyer)


def select_specialist(step_input: StepInput) -> list[Step]:
    route = parse_route(str(step_input.previous_step_content or ""))
    return [lawyer_step if route == "lawyer" else architect_step]


# Scenario 1: same flow as app.py's agent="auto" (classify, then answer)
route_workflow = Workflow(
    id="route",
    name="Auto-routed query",
    steps=[
        Step(name="coordinator", agent=coordinator),
        Router(name="specialist", selector=select_specialist,
               choices=[architect_step, lawyer_step]),
    ],
    telemetry=False,
)

# Scenario 2: architect designs, lawyer reviews the technologies it picked
pipeline_workflow = Workflow(
    id="pipeline",
    name="Architecture + license review",
    steps=[Step(name="architect", agent=architect), Step(name="lawyer", agent=lawyer)],
    telemetry=False,
)


agent_os = AgentOS(
    id="agentic-demo",
    description="Architect/Lawyer demo on Agno AgentOS",
    agents=[coordinator, architect, lawyer],
    workflows=[route_workflow, pipeline_workflow],
    db=SqliteDb(db_file="tmp/agentos.db"),
    telemetry=False,
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="agentos_app:app", host="0.0.0.0", port=8080)
