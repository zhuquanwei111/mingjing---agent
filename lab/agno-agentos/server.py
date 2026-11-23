"""Real AgentOS agents, a fixed workflow, and a sibling deterministic API route."""
import os
import uuid

import uvicorn
from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.os import AgentOS, QueueConfig
from agno.os.settings import AgnoAPISettings
from agno.tools import tool
from agno.workflow import Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from control import GATE, NAME, SCOPES, dispatch, record

db = PostgresDb(db_url=os.environ["PRODUCT_DSN"].replace("postgresql://", "postgresql+psycopg://", 1))


@tool(name=NAME, external_execution=True)
def request_receipt(ref: str) -> str:
    """Submit a record reference and obtain an independent receipt."""
    raise AssertionError("AgentOS must yield this tool for external execution")


def run_deterministic(scope: str, ref: str) -> str:
    run = uuid.uuid4().hex
    record(scope, run, scope, "call_" + uuid.uuid4().hex, ref)
    dispatch(scope)
    return run


def workflow_step(step_input: StepInput) -> StepOutput:
    return StepOutput(content=run_deterministic("workflow", str(step_input.input)))


class DirectInput(BaseModel):
    ref: str


base = FastAPI()


@base.post("/fixture/direct")
def direct(item: DirectInput, authorization: str = Header()):
    if authorization != "Bearer " + os.environ["OS_KEY"]:
        raise HTTPException(status_code=403)
    return {"run_id": run_deterministic("direct", item.ref)}


def model(scope):
    return OpenAIChat(id="fixture", api_key="synthetic", base_url=f"{GATE}/{scope}/v1", max_retries=0)


agents = [Agent(id=scope, name=scope, model=model(scope), db=db, tools=[request_receipt],
                retries=0, telemetry=False) for scope in SCOPES]
workflow = Workflow(id="fixed", name="fixed", db=db, steps=[Step(name="submit", executor=workflow_step)])
runtime = AgentOS(id="comparison", agents=agents, workflows=[workflow], db=db, base_app=base,
                  settings=AgnoAPISettings(os_security_key=os.environ["OS_KEY"]), telemetry=False, mcp=False,
                  queue=QueueConfig(durable=True, max_attempts=1, poll_interval=.2))
app = runtime.get_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8090, log_level="error")
