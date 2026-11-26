"""Worker entry point, with one plugin and a dedicated queue per test harness."""

import asyncio
import os
from datetime import timedelta

from langgraph.errors import GraphRecursionError
from temporalio.client import Client
from temporalio.langgraph import LangGraphPlugin
from temporalio.worker import Worker

from mingjing_p1.agent.graph import build_graph
from mingjing_p1.telemetry import configure, interceptor
from mingjing_p1.temporal.activities import agent_tool, execute_job, reject_agent
from mingjing_p1.temporal.workflows import RETRY, Gateway, MarkerChild
from temporalio import workflow


async def run() -> None:
    configure()
    client = await Client.connect(
        os.environ["TEMPORAL_ADDRESS"], namespace=os.environ["TEMPORAL_NAMESPACE"],
        interceptors=[interceptor()],
    )
    plugin = LangGraphPlugin(
        graphs={"p1-agent": build_graph(agent_tool)},
        default_activity_options={
            "start_to_close_timeout": timedelta(seconds=20),
            "heartbeat_timeout": timedelta(seconds=2),
            "schedule_to_close_timeout": timedelta(seconds=30),
            "retry_policy": RETRY,
            "cancellation_type": workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        },
    )
    worker = Worker(
        client, task_queue=os.environ["TEMPORAL_TASK_QUEUE"], workflows=[Gateway, MarkerChild],
        activities=[execute_job, reject_agent], plugins=[plugin],
        workflow_failure_exception_types=[GraphRecursionError],
        default_heartbeat_throttle_interval=timedelta(milliseconds=200),
        max_heartbeat_throttle_interval=timedelta(milliseconds=300),
    )
    print("WORKER_READY", flush=True)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run())
