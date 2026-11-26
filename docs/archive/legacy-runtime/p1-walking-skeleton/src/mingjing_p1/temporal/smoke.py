"""Provider-free smoke tests for the pinned SDK and plugin."""

import asyncio
import json
import os
import sys
from datetime import timedelta
from typing import TypedDict
from uuid import uuid4

from langgraph.func import entrypoint, task
from langgraph.graph import END, START, StateGraph
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.langgraph import LangGraphPlugin, entrypoint as temporal_entrypoint
from temporalio.langgraph import graph
from temporalio.worker import Worker


class SmokeState(TypedDict):
    value: str


@activity.defn
async def marker(value: str) -> str:
    return f"synthetic:{value}"


@task
async def functional_marker(value: str) -> str:
    return await marker(value)


@entrypoint()
async def functional_graph(value: str) -> str:
    return await functional_marker(value)


async def graph_marker(state: SmokeState) -> SmokeState:
    return {"value": await marker(state["value"])}


@workflow.defn
class SmokePlain:
    @workflow.run
    async def run(self, value: str) -> str:
        return await workflow.execute_activity(
            marker, value, start_to_close_timeout=timedelta(seconds=5)
        )


@workflow.defn
class SmokeGraph:
    @workflow.run
    async def run(self, value: str) -> str:
        result = await graph("smoke").compile().ainvoke({"value": value})
        return result["value"]


@workflow.defn
class SmokeFunctional:
    @workflow.run
    async def run(self, value: str) -> str:
        return await temporal_entrypoint("smoke-functional").ainvoke(value)


def make_worker(client: Client, queue: str) -> Worker:
    state_graph = StateGraph(SmokeState)
    state_graph.add_node("marker", graph_marker, metadata={"execute_in": "activity"})
    state_graph.add_edge(START, "marker")
    state_graph.add_edge("marker", END)
    plugin = LangGraphPlugin(
        graphs={"smoke": state_graph},
        entrypoints={"smoke-functional": functional_graph},
        tasks=[functional_marker],
        activity_options={"functional_marker": {"execute_in": "activity"}},
        default_activity_options={"start_to_close_timeout": timedelta(seconds=5)},
    )
    return Worker(
        client, task_queue=queue,
        workflows=[SmokePlain, SmokeGraph, SmokeFunctional],
        activities=[marker], plugins=[plugin],
    )


async def connect() -> Client:
    return await Client.connect(
        os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:7233"),
        namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
    )


async def run_smoke(client: Client, queue: str) -> dict[str, str]:
    results = {}
    for workflow_type in (SmokePlain, SmokeGraph, SmokeFunctional):
        handle = await client.start_workflow(
            workflow_type.run, "p1-smoke", id=f"p1-smoke-{uuid4()}",
            task_queue=queue, execution_timeout=timedelta(seconds=20),
        )
        results[workflow_type.__name__] = await handle.result()
        history = await handle.fetch_history()
        assert any(event.HasField("activity_task_completed_event_attributes")
                   for event in history.events)
    return results


async def main(mode: str) -> None:
    client = await connect()
    queue = os.environ.get("TEMPORAL_TASK_QUEUE", "p1-cli-smoke")
    if mode == "worker":
        await make_worker(client, queue).run()
    elif mode == "run":
        print(json.dumps(await run_smoke(client, queue)))
    else:
        raise SystemExit("usage: python -m mingjing_p1.temporal.smoke worker|run")


if __name__ == "__main__":
    # Importable definitions retain stable names when using the module entry point.
    from mingjing_p1.temporal.smoke import main as cli_main

    asyncio.run(cli_main(sys.argv[1]))
