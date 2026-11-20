import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from temporalio import activity
from temporalio.client import Client
from temporalio.common import VersioningBehavior, WorkerDeploymentVersion, WorkflowIDReusePolicy
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.exceptions import ApplicationError, WorkflowAlreadyStartedError
from temporalio.langgraph import LangGraphPlugin
from temporalio.service import RPCError, RPCStatusCode
from temporalio.worker import Worker, WorkerDeploymentConfig

from .contracts import Kind
from .service import Service, TERMINAL
from .workflows import OPTIONS, TaskJob, TaskWorkflow

START_RETRY_WINDOW = timedelta(minutes=5)


class AgentState(TypedDict, total=False):
    task_id: str
    tool: str
    done: bool


async def choose_note_tool(state: AgentState) -> dict:
    return {"tool": "append_note"}

def activity_deadline() -> datetime | None:
    info = activity.info()
    possible = [
        timestamp + timeout
        for timestamp, timeout in (
            (info.started_time, info.start_to_close_timeout),
            (info.scheduled_time, info.schedule_to_close_timeout),
        ) if timeout is not None
    ]
    return min(possible, default=None)


def make_worker(client: Client, queue: str, service: Service, deployment=None) -> Worker:
    @activity.defn(name="mingjing.check.v1")
    async def ready(task: str) -> str:
        task_id = UUID(task)
        await asyncio.to_thread(service.engine, task_id, "running", activity.info().workflow_run_id)
        return await asyncio.to_thread(service.readiness, task_id)

    @activity.defn(name="mingjing.execute.v1")
    async def execute(task: str) -> None:
        if not await asyncio.to_thread(service.execute, UUID(task), deadline=activity_deadline()):
            raise ApplicationError("execution in progress", type="ExecutionInProgress")

    async def use_note_tool(state: AgentState) -> dict:
        if not await asyncio.to_thread(
            service.execute, UUID(state["task_id"]), agent_tool=state["tool"], deadline=activity_deadline(),
        ):
            raise ApplicationError("execution in progress", type="ExecutionInProgress")
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

    def owns(self, view: dict) -> bool:
        return (view["environment"] == self.service.catalog.environment
                and view["run"]["namespace"] == os.environ["TEMPORAL_NAMESPACE"])

    @staticmethod
    def start_window_closed(view: dict) -> bool:
        first = view["run"]["first_start_at"]
        return first is not None and datetime.now(UTC) >= first + START_RETRY_WINDOW

    async def start(self, view: dict) -> None:
        task_id = UUID(view["task_id"])
        if view["environment"] != self.service.catalog.environment:
            return
        lock = await asyncio.to_thread(self.service.lock_engine_start, task_id)
        if lock is None:
            return
        try:
            view = await asyncio.to_thread(self.service.bind_engine_start, task_id, os.environ["TEMPORAL_NAMESPACE"])
            if not self.owns(view) or view["state"] in TERMINAL:
                return
            if not view["run"]["temporal_run_id"] and not self.start_window_closed(view):
                client = await connect()
                cap = self.service.catalog.implementation(view["capability_id"], view["version"])
                try:
                    handle = await client.start_workflow(
                        TaskWorkflow.run, TaskJob(str(task_id), cap.kind == Kind.AGENT),
                        id=view["run"]["workflow_id"], task_queue=self.queue,
                        id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                        execution_timeout=timedelta(hours=24), rpc_timeout=timedelta(seconds=5),
                    )
                except WorkflowAlreadyStartedError:
                    pass
                else:
                    await asyncio.to_thread(self.service.engine, task_id, "running", handle.first_execution_run_id)
                    return
        finally:
            await asyncio.to_thread(lock.close)
        await self.refresh(view)

    async def refresh(self, view: dict) -> None:
        if not self.owns(view):
            return
        client = await connect()
        recorded_run = view["run"]["temporal_run_id"]
        handle = client.get_workflow_handle(view["run"]["workflow_id"], run_id=recorded_run)
        try:
            info = await handle.describe(rpc_timeout=timedelta(seconds=3))
        except RPCError as error:
            if error.status != RPCStatusCode.NOT_FOUND:
                raise
            if recorded_run or self.start_window_closed(view):
                await asyncio.to_thread(
                    self.service.engine, UUID(view["task_id"]), "history_unavailable", recorded_run, wait=False,
                )
            return
        if info.status:
            await asyncio.to_thread(
                self.service.engine, UUID(view["task_id"]), info.status.name.lower(), info.run_id, wait=False,
            )

    async def control(self, view: dict, *, cancel: bool = False) -> None:
        if not self.owns(view):
            return
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
