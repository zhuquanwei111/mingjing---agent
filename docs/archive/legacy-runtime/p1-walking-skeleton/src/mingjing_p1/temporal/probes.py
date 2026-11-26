"""Deterministic plugin probes. These run only against the isolated Server."""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

from temporalio import activity, workflow
from temporalio.client import Client, WorkflowHistory
from temporalio.common import VersioningBehavior, WorkerDeploymentVersion
from temporalio.exceptions import ApplicationError
from temporalio.worker import Replayer, Worker, WorkerDeploymentConfig

with workflow.unsafe.imports_passed_through():
    from langgraph.config import get_stream_writer
    from langgraph.func import entrypoint, task
    from langgraph.graph import END, START, StateGraph
    from temporalio.contrib.pydantic import pydantic_data_converter
    from temporalio.contrib.workflow_streams import WorkflowStream
    from temporalio.langgraph import LangGraphPlugin, cache, graph
    from temporalio.langgraph import entrypoint as workflow_entrypoint
    import temporalio.langgraph as integration

    from mingjing_p1.temporal.activities import barrier
    from mingjing_p1.temporal.probe_models import Cursor, Detail, StreamInput, TypedInput
    from mingjing_p1.temporal.workflows import RETRY


async def numbered(state: dict) -> dict:
    info = activity.info()
    return {"serial": f"{info.workflow_run_id}:{info.activity_id}"}


def numbered_graph(node: str = "numbered"):
    # A dict boundary intentionally makes the matched call input unambiguous.
    from typing_extensions import TypedDict

    class State(TypedDict, total=False):
        value: str
        serial: str

    builder = StateGraph(State)
    builder.add_node(node, numbered, metadata={"execute_in": "activity"})
    builder.add_edge(START, node)
    builder.add_edge(node, END)
    return builder


@workflow.defn
class CacheAcrossRuns:
    @workflow.run
    async def run(self, cursor: Cursor) -> dict:
        app = graph("cache-probe", cache=cursor.carried).compile()
        first = (await app.ainvoke({"value": "same"}))["serial"]
        second = (await app.ainvoke({"value": "same"}))["serial"]
        if cursor.phase == 0:
            workflow.continue_as_new(Cursor(1, cache(), [first, second]))
        return {"prior": cursor.first_serials, "current": [first, second], "cursor": cursor.phase}


@workflow.defn(versioning_behavior=VersioningBehavior.PINNED)
class LegacyCacheProbe:
    def __init__(self) -> None:
        self.serials: list[str] = []
        self.released = False

    @workflow.query
    def observations(self) -> list[str]:
        return self.serials

    @workflow.signal
    def release(self) -> None:
        self.released = True

    @workflow.run
    async def run(self, value: str) -> list[str]:
        app = graph("cache-probe").compile()
        self.serials = [(await app.ainvoke({"value": value}))["serial"],
                        (await app.ainvoke({"value": value}))["serial"]]
        await workflow.wait_condition(lambda: self.released)
        return self.serials


@task
async def typed_echo(value: TypedInput) -> TypedInput:
    if activity.info().attempt == 1:
        raise ApplicationError("synthetic retry", type="SyntheticRetry")
    assert isinstance(value.detail, Detail)
    assert isinstance(value.detail.at, datetime)
    assert isinstance(value.detail.identifier, UUID)
    return value


@entrypoint()
async def typed_program(value: TypedInput) -> TypedInput:
    return await typed_echo(value)


@workflow.defn
class FunctionalReplay:
    def __init__(self) -> None:
        self.ready = False
        self.released = False

    @workflow.query
    def observed(self) -> bool:
        return self.ready

    @workflow.signal
    def release(self) -> None:
        self.released = True

    @workflow.run
    async def run(self, value: TypedInput) -> TypedInput:
        output = await workflow_entrypoint("typed").ainvoke(value)
        assert isinstance(output, TypedInput)
        assert output.messages[0].id == value.messages[0].id
        self.ready = True
        await workflow.wait_condition(lambda: self.released)
        return output


async def emit(state: dict) -> dict:
    info = activity.info()
    get_stream_writer()({"event_id": "marker:1", "attempt": info.attempt})
    await barrier("stream", "marker:1")
    return {"value": "stream-complete"}


@workflow.defn
class StreamReplay:
    @workflow.init
    def __init__(self, value: StreamInput) -> None:
        self.stream = WorkflowStream(prior_state=value.stream)
        self.closed = False

    @workflow.signal
    def close(self) -> None:
        self.closed = True

    @workflow.run
    async def run(self, value: StreamInput) -> str:
        if value.stage == 0:
            app = graph("stream-probe").compile()
            async for chunk in app.astream({"value": "start"}, stream_mode="updates"):
                self.stream.topic("updates").publish({"nodes": list(chunk)})
            await self.stream.continue_as_new(lambda state: [StreamInput(1, state)])
        self.stream.topic("progress").publish({"event_id": "done", "attempt": 0})
        await workflow.wait_condition(lambda: self.closed)
        return "stream-complete"


def fixture(mode: str, *, rename: bool = False) -> tuple[type, LangGraphPlugin]:
    options = {
        "start_to_close_timeout": timedelta(seconds=20),
        "heartbeat_timeout": timedelta(seconds=2),
        "retry_policy": RETRY,
    }
    if mode == "functional":
        return FunctionalReplay, LangGraphPlugin(
            entrypoints={"typed": typed_program}, tasks=[typed_echo],
            activity_options={"typed_echo": {"execute_in": "activity"}},
            default_activity_options={"start_to_close_timeout": timedelta(seconds=12),
                                      "retry_policy": RETRY},
        )
    if mode == "stream":
        builder = StateGraph(dict)
        builder.add_node("emit", emit, metadata={"execute_in": "activity"})
        builder.add_edge(START, "emit")
        builder.add_edge("emit", END)
        return StreamReplay, LangGraphPlugin(
            graphs={"stream-probe": builder}, default_activity_options=options,
            streaming_topic="progress", streaming_batch_interval=timedelta(milliseconds=50),
        )
    flow = LegacyCacheProbe if mode == "version" else CacheAcrossRuns
    return flow, LangGraphPlugin(
        graphs={"cache-probe": numbered_graph("renamed" if rename else "numbered")},
        default_activity_options=options,
    )


async def replay(mode: str, workflow_id: str, history_file: Path, rename=False):
    flow, plugin = fixture(mode, rename=rename)
    replayer = Replayer(workflows=[flow], plugins=[plugin], data_converter=pydantic_data_converter)
    history = WorkflowHistory.from_json(workflow_id, history_file.read_text())
    return await replayer.replay_workflow(history, raise_on_replay_failure=False)


async def run() -> None:
    mode = os.environ["P1_PROBE_MODE"]
    print(f"PLUGIN_VERSION {version('temporalio-langgraph')}", flush=True)
    print(f"PLUGIN_MODULE {integration.__file__}", flush=True)
    if len(sys.argv) > 1 and sys.argv[1] == "replay":
        result = await replay(mode, sys.argv[2], Path(sys.argv[3]))
        failure = result.replay_failure
        print(json.dumps({"failure": type(failure).__name__ if failure else None,
                          "message": str(failure) if failure else None}))
        return
    flow, plugin = fixture(mode)
    client = await Client.connect(
        os.environ["TEMPORAL_ADDRESS"], namespace=os.environ["TEMPORAL_NAMESPACE"],
        data_converter=pydantic_data_converter,
    )
    deployment = None
    if mode == "version":
        deployment = WorkerDeploymentConfig(
            version=WorkerDeploymentVersion(os.environ["P1_DEPLOYMENT"], os.environ["P1_BUILD"]),
            use_worker_versioning=True,
        )
    worker = Worker(
        client, task_queue=os.environ["TEMPORAL_TASK_QUEUE"], workflows=[flow], plugins=[plugin],
        deployment_config=deployment,
        default_heartbeat_throttle_interval=timedelta(milliseconds=150),
        max_heartbeat_throttle_interval=timedelta(milliseconds=300),
    )
    print("PROBE_READY", flush=True)
    await worker.run()


if __name__ == "__main__":
    # Keep module-qualified models and task names stable in history.
    from mingjing_p1.temporal.probes import run as cli_run

    asyncio.run(cli_run())
