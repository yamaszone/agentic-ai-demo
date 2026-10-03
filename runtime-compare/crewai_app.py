#!/usr/bin/env python3
"""The demo's coordinator/architect/lawyer agents on CrewAI.

CrewAI ships no HTTP runtime, so the FastAPI layer is hand-written here
and mirrors app.py's /query contract.

Run:  python crewai_app.py   ->  http://localhost:8081/docs
"""

from typing import Literal

from crewai import LLM, Agent, Crew, Process, Task
from crewai.events.utils.console_formatter import set_suppress_console_output
from crewai.flow.flow import Flow, listen, router, start
from fastapi import FastAPI
from pydantic import BaseModel

from common import AGENT_PROMPTS, LLM_API_KEY, LLM_BASE_URL, MODEL_NAME, parse_route


def _llm(temperature: float = 0.7) -> LLM:
    return LLM(model=f"openai/{MODEL_NAME}", base_url=LLM_BASE_URL, api_key=LLM_API_KEY,
               temperature=temperature, max_tokens=1024)


coordinator = Agent(role="AI Coordinator", goal="Route each request to the right specialist",
                    backstory=AGENT_PROMPTS["coordinator"], llm=_llm(0.3),
                    allow_delegation=False, max_iter=1)
architect = Agent(role="Software Architect", goal="Design practical, production-ready systems",
                  backstory=AGENT_PROMPTS["architect"], llm=_llm(), allow_delegation=False)
lawyer = Agent(role="Open Source License Attorney",
               goal="Assess open source licenses for commercial use",
               backstory=AGENT_PROMPTS["lawyer"], llm=_llm(), allow_delegation=False)
SPECIALISTS = {"architect": architect, "lawyer": lawyer}


class RouteState(BaseModel):
    query: str = ""
    agent: str = ""
    response: str = ""


# Scenario 1: same flow as app.py's agent="auto" (classify, then answer)
class RouteFlow(Flow[RouteState]):
    @start()
    def classify(self):
        self.state.agent = parse_route(coordinator.kickoff(self.state.query).raw)

    @router(classify)
    def pick(self):
        return self.state.agent

    @listen("architect")
    def answer_architect(self):
        self.state.response = architect.kickoff(self.state.query).raw

    @listen("lawyer")
    def answer_lawyer(self):
        self.state.response = lawyer.kickoff(self.state.query).raw


# Scenario 2: architect designs, lawyer reviews the technologies it picked
def pipeline_crew() -> Crew:
    design = Task(description="{query}", agent=architect,
                  expected_output="Architecture options, technologies, complexity, timeline")
    review = Task(description="Review the licenses of every technology in the design.",
                  agent=lawyer, context=[design],
                  expected_output="Per-technology license, commercial use, risk")
    return Crew(agents=[architect, lawyer], tasks=[design, review],
                process=Process.sequential, verbose=False)


def run_route(query: str, agent: str = "auto") -> RouteState:
    set_suppress_console_output(True)  # Flow always prints Rich panels otherwise
    if agent != "auto":
        return RouteState(query=query, agent=agent,
                          response=SPECIALISTS[agent].kickoff(query).raw)
    flow = RouteFlow()
    flow.kickoff(inputs={"query": query})
    return flow.state


def run_pipeline(query: str) -> dict:
    out = pipeline_crew().kickoff(inputs={"query": query})
    return {"architect": out.tasks_output[0].raw, "lawyer": out.tasks_output[1].raw}


app = FastAPI(title="Multi-Agent AI Demo (CrewAI)")


class AgentRequest(BaseModel):
    query: str
    agent: Literal["architect", "lawyer", "auto"] = "auto"


@app.get("/health")
def health():
    return {"status": "healthy", "llm_base_url": LLM_BASE_URL}


@app.post("/query")
def query(request: AgentRequest):
    state = run_route(request.query, request.agent)
    return {"agent": state.agent, "query": state.query, "response": state.response}


@app.post("/pipeline")
def pipeline(request: AgentRequest):
    return run_pipeline(request.query)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
