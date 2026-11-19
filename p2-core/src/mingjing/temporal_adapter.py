import asyncio
import os
from datetime import timedelta
from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from temporalio import activity
from temporalio.client import Client
from temporalio.common import VersioningBehavior, WorkerDeploymentVersion, WorkflowIDReusePolicy
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.langgraph import LangGraphPlugin
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Worker, WorkerDeploymentConfig

from .contracts import Kind
from .service import Service
from .workflows import OPTIONS, TaskJob, TaskWorkflow


class AgentState(TypedDict, total=False):
    task_id: str
    tool: str
    done: bool


async def choose_note_tool(state: AgentState) -> dict:
    return {"tool": "append_note"}


def make_worker(client: Client, queue: str, service: Service, deployment=None) -> Worker:
    @activity.defn(name="mingjing.check.v1")
    async def ready(task: str) -> str:
        task_id = UUID(task)
        await asyncio.to_thread(service.engine, task_id, "running", activity.info().workflow_run_id)
        return await asyncio.to_thread(service.readiness, task_id)

    @activity.defn(name="mingjing.execute.v1")
    async def execute(task: str) -> None:
        await asyncio.to_thread(service.execute, UUID(task))

    async def use_note_tool(state: AgentState) -> dict:
        await asyncio.to_thread(service.execute, UUID(state["task_id"]), agent_tool=state["tool"])
        return {"done": True}

    agent = StateGraph(AgentState)
    agent.add_node("choose", choose_note_tool, metadata={"execute_in": "workflow"})
    agent.add_node("tool", use_note_tool, metadata={"execute_in": "activity"})
    agent.add_edge(START, "choose")
    agent.add_edge("choose", "tool")
    agent.add_edge("tool", END)
    plugin = LangGraphPlugin(graphs={"mingjing.agent.v1": agent}, default_activity_options=OPTIONS)
    return Worker(
        client, task_queue=queue, workflows=[TaskWorkflow], activities=[ready, execute],
        plugins=[plugin], deployment_config=deployment,
    )


async def connect() -> Client:
    return await Client.connect(
        os.environ["TEMPORAL_ADDRESS"], namespace=os.environ["TEMPORAL_NAMESPACE"],
        interceptors=[TracingInterceptor()],
    )


def deployment_from_environment() -> WorkerDeploymentConfig | None:
    name = os.environ.get("MINGJING_WORKER_DEPLOYMENT")
    build = os.environ.get("MINGJING_WORKER_BUILD")
    if not name and not build:
        return None
    if not name or not build:
        raise ValueError("configure both worker deployment and build")
    return WorkerDeploymentConfig(
        version=WorkerDeploymentVersion(name, build), use_worker_versioning=True,
        default_versioning_behavior=VersioningBehavior.PINNED,
    )


class TemporalAdapter:
    def __init__(self, service: Service, queue: str):
        self.service = service
        self.queue = queue

    async def start(self, view: dict) -> None:
        client = await connect()
        task_id = view["task_id"]
        cap = self.service.catalog.implementation(view["capability_id"], view["version"])
        try:
            handle = await client.start_workflow(
                TaskWorkflow.run, TaskJob(task_id, cap.kind == Kind.AGENT),
                id=view["run"]["workflow_id"], task_queue=self.queue,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                execution_timeout=timedelta(hours=24), rpc_timeout=timedelta(seconds=5),
            )
        except WorkflowAlreadyStartedError:
            await self.refresh(view)
        else:
            await asyncio.to_thread(self.service.engine, UUID(task_id), "running", handle.first_execution_run_id)

    async def refresh(self, view: dict) -> None:
        client = await connect()
        handle = client.get_workflow_handle(view["run"]["workflow_id"])
        try:
            info = await handle.describe(rpc_timeout=timedelta(seconds=3))
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
            return
        if info.status:
            await asyncio.to_thread(self.service.engine, UUID(view["task_id"]), info.status.name.lower(), info.run_id)

    async def control(self, view: dict, *, cancel: bool = False) -> None:
        client = await connect()
        handle = client.get_workflow_handle(view["run"]["workflow_id"])
        try:
            if cancel:
                await handle.cancel(rpc_timeout=timedelta(seconds=3))
            else:
                await handle.signal(TaskWorkflow.notify, rpc_timeout=timedelta(seconds=3))
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
