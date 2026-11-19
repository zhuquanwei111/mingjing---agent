import asyncio
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import HumanMessage
from temporalio.api.deployment.v1 import WorkerDeploymentVersion
from temporalio.api.workflowservice.v1 import (
    DescribeWorkerDeploymentVersionRequest,
    SetWorkerDeploymentCurrentVersionRequest,
)
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.contrib.workflow_streams import WorkflowStreamClient
from temporalio.service import RPCError

from conftest import evidence
from mingjing_p1.temporal.probe_models import Cursor, Detail, StreamInput, TypedInput
from mingjing_p1.temporal.probes import CacheAcrossRuns, FunctionalReplay, LegacyCacheProbe, StreamReplay, replay

LEGACY = "/opt/legacy/bin/python"


async def connect() -> Client:
    return await Client.connect(os.environ["TEMPORAL_ADDRESS"], namespace=os.environ["TEMPORAL_NAMESPACE"],
                                data_converter=pydantic_data_converter)


async def probe(rig, mode, label="first", *, legacy=False, **extra):
    environment = rig.env(rig.queue, P1_PROBE_MODE=mode, **extra)
    args = {"executable": LEGACY} if legacy else {}
    worker = rig.launch(label, "mingjing_p1.temporal.probes", environment, **args)
    await worker.ready("PROBE_READY")
    return worker


async def query_until(handle, query, *, timeout=20):
    async with asyncio.timeout(timeout):
        while True:
            try:
                if result := await handle.query(query, rpc_timeout=timedelta(seconds=1)):
                    return result
            except RPCError:
                description = await handle.describe()
                if description.status != WorkflowExecutionStatus.RUNNING:
                    return await handle.result()
            await asyncio.sleep(0.1)


def persist(history, name, fallback: Path) -> Path:
    evidence_dir = Path("/evidence")
    path = (evidence_dir if evidence_dir.is_dir() else fallback) / f"{name}.history.json"
    path.write_text(history.to_json())
    return path


def activities_in(history):
    return [e.activity_task_scheduled_event_attributes.activity_type.name for e in history.events
            if e.HasField("activity_task_scheduled_event_attributes")]


def test_at09_graph_continue_as_new_cache(rig):
    async def run():
        await probe(rig, "cache")
        client = await connect()
        handle = await client.start_workflow(CacheAcrossRuns.run, Cursor(), id=f"cache-{uuid4()}",
                                             task_queue=rig.queue, execution_timeout=timedelta(seconds=40))
        result = await asyncio.wait_for(handle.result(), 25)
        assert result["cursor"] == 1
        assert result["prior"][0] != result["prior"][1]
        assert result["current"][0] == result["prior"][1]
        assert result["current"][1] not in result["prior"]
        first = await client.get_workflow_handle(handle.id, run_id=handle.first_execution_run_id).fetch_history()
        next_run = next(e.workflow_execution_continued_as_new_event_attributes.new_execution_run_id
                        for e in first.events if e.HasField("workflow_execution_continued_as_new_event_attributes"))
        second = await client.get_workflow_handle(handle.id, run_id=next_run).fetch_history()
        assert len(activities_in(first)) == 2 and len(activities_in(second)) == 1
        first_path = persist(first, "AT09-cache-before", rig.root)
        second_path = persist(second, "AT09-cache-after", rig.root)
        assert not (await replay("cache", handle.id, first_path)).replay_failure
        assert not (await replay("cache", handle.id, second_path)).replay_failure
        evidence("AT09-cache", {"first_run": handle.first_execution_run_id, "second_run": next_run,
                               "scheduled_per_run": [2, 1], "serials": result, "same_version_replay": "passed"})

    asyncio.run(run())


def test_at09_functional_retry_typed_cold_replay(rig):
    async def run():
        first = await probe(rig, "functional")
        client = await connect()
        typed = TypedInput(detail=Detail(at=datetime(2026, 11, 19, tzinfo=UTC), identifier=uuid4()),
                           messages=[HumanMessage(content="synthetic marker", id="message-1")])
        handle = await client.start_workflow(FunctionalReplay.run, typed, id=f"functional-{uuid4()}",
                                             task_queue=rig.queue, execution_timeout=timedelta(seconds=50))
        assert await query_until(handle, FunctionalReplay.observed)
        first.stop(kill=True)
        await probe(rig, "functional", "replacement")
        assert await query_until(handle, FunctionalReplay.observed)
        await handle.signal(FunctionalReplay.release)
        result = await asyncio.wait_for(handle.result(), 25)
        assert result == typed and isinstance(result.messages[0], HumanMessage)
        history = await handle.fetch_history()
        starts = [event.activity_task_started_event_attributes.attempt for event in history.events
                  if event.HasField("activity_task_started_event_attributes")]
        assert starts == [2] and len(activities_in(history)) == 1
        path = persist(history, "AT09-functional", rig.root)
        assert not (await replay("functional", handle.id, path)).replay_failure
        evidence("AT09-functional", {"worker_exit": first.process.returncode, "attempt": starts[0],
                                     "scheduled_activities": len(activities_in(history)),
                                     "typed_roundtrip": result.model_dump(mode="json"), "replay": "passed"})

    asyncio.run(run())


def test_at09_graph_interrupt_cold_replay(rig):
    async def run():
        worker = await rig.worker("interrupted")
        api = await rig.api()
        client = await rig.client()
        task = api.submit("agent")
        handle = client.get_workflow_handle(task["workflow_id"])
        await rig.waiting(handle)
        worker.stop(kill=True)
        await rig.worker("replacement")
        await rig.waiting(handle)
        assert api.approve(task)[0] == 202
        output = await asyncio.wait_for(handle.result(), 25)
        assert output["state"] == "succeeded"
        relevant = activities_in(await handle.fetch_history())
        assert relevant.count("p1-agent.approval") == 2
        assert relevant.count("p1-agent.tool") == 1
        evidence("AT09-interrupt", {"worker_exit": worker.process.returncode,
                                    "activity_types": relevant, "state": output["state"]})

    asyncio.run(run())


def test_at09_stream_retry_resume_dedupe_across_run(rig):
    async def run():
        control = rig.hold("stream", "stream")
        first = await probe(rig, "stream", MINGJING_PROBE_DIR=str(control))
        client = await connect()
        handle = await client.start_workflow(StreamReplay.run, StreamInput(), id=f"streams-{uuid4()}",
                                             task_queue=rig.queue, execution_timeout=timedelta(seconds=60))
        stream = WorkflowStreamClient.create(client, handle.id)
        topic = stream.topic("progress", type=dict)
        await rig.reached(control, "stream", "marker:1")
        values = []
        async with asyncio.timeout(10):
            subscriber = topic.subscribe(from_offset=0)
            event = await anext(subscriber)
            await subscriber.aclose()
        assert event.data == {"event_id": "marker:1", "attempt": 1}
        values.append((event.offset, event.data))
        first.stop(kill=True)
        await probe(rig, "stream", "replacement")
        async with asyncio.timeout(28):
            subscriber = topic.subscribe(from_offset=event.offset + 1)
            try:
                async for item in subscriber:
                    values.append((item.offset, item.data))
                    if item.data["event_id"] == "done":
                        break
            finally:
                await subscriber.aclose()
        deduped = list(dict.fromkeys(event["event_id"] for _, event in values))
        assert deduped == ["marker:1", "done"]
        assert [event["attempt"] for _, event in values] == [1, 2, 0]
        offsets = [offset for offset, _ in values]
        assert offsets == sorted(set(offsets))
        updates = stream.topic("updates", type=dict).subscribe(from_offset=0)
        update = await asyncio.wait_for(anext(updates), 10)
        await updates.aclose()
        assert update.data == {"nodes": ["emit"]}
        await handle.signal(StreamReplay.close)
        assert await asyncio.wait_for(handle.result(), 20) == "stream-complete"
        first_history = await client.get_workflow_handle(handle.id, run_id=handle.first_execution_run_id).fetch_history()
        assert any(e.HasField("workflow_execution_continued_as_new_event_attributes") for e in first_history.events)
        evidence("AT09-stream", {"events": values, "deduped": deduped,
                                 "updates_bridge": update.data, "continued_as_new": True,
                                 "cancelled_worker_exit": first.process.returncode,
                                 "result": "stream-complete"})

    asyncio.run(run())


async def select_current(client, deployment, build):
    namespace = os.environ["TEMPORAL_NAMESPACE"]
    async with asyncio.timeout(20):
        while True:
            try:
                await client.workflow_service.describe_worker_deployment_version(
                    DescribeWorkerDeploymentVersionRequest(
                        namespace=namespace, deployment_version=WorkerDeploymentVersion(
                            deployment_name=deployment, build_id=build,
                        ),
                    ),
                )
                await client.workflow_service.set_worker_deployment_current_version(
                    SetWorkerDeploymentCurrentVersionRequest(namespace=namespace, deployment_name=deployment,
                                                             build_id=build, identity="p1-acceptance"),
                )
                return
            except RPCError:
                await asyncio.sleep(0.3)


def legacy_replay(rig, workflow_id, path):
    process = subprocess.run(
        [LEGACY, "-m", "mingjing_p1.temporal.probes", "replay", workflow_id, str(path)],
        env=rig.env(rig.queue, P1_PROBE_MODE="version"), capture_output=True, text=True, timeout=20,
        check=True,
    )
    assert "PLUGIN_VERSION 0.1.0" in process.stdout
    assert "PLUGIN_MODULE /opt/legacy/" in process.stdout
    return json.loads(process.stdout.splitlines()[-1])


def builds(history):
    return sorted({e.workflow_task_completed_event_attributes.deployment_version.build_id
                   for e in history.events if e.HasField("workflow_task_completed_event_attributes")
                   and e.workflow_task_completed_event_attributes.HasField("deployment_version")})


def test_at10_version_routing_and_replay_boundaries(rig):
    async def run():
        deployment = f"p1-{rig.tenant}"
        old_worker = await probe(rig, "version", "plugin-0", legacy=True,
                                 P1_DEPLOYMENT=deployment, P1_BUILD="plugin-0-1-0")
        assert "PLUGIN_VERSION 0.1.0" in old_worker.log.read_text()
        assert "PLUGIN_MODULE /opt/legacy/" in old_worker.log.read_text()
        client = await connect()
        await select_current(client, deployment, "plugin-0-1-0")
        previous = await client.start_workflow(LegacyCacheProbe.run, "same", id=f"legacy-{uuid4()}",
                                               task_queue=rig.queue, execution_timeout=timedelta(seconds=90))
        prior = await query_until(previous, LegacyCacheProbe.observations)
        assert prior[0] == prior[1], prior
        new_worker = await probe(rig, "version", "plugin-1", P1_DEPLOYMENT=deployment, P1_BUILD="plugin-1-0-0")
        assert "PLUGIN_VERSION 1.0.0" in new_worker.log.read_text()
        await select_current(client, deployment, "plugin-1-0-0")
        upgraded = await client.start_workflow(LegacyCacheProbe.run, "same", id=f"upgraded-{uuid4()}",
                                               task_queue=rig.queue, execution_timeout=timedelta(seconds=90))
        latest = await query_until(upgraded, LegacyCacheProbe.observations)
        assert latest[0] != latest[1], latest
        await previous.signal(LegacyCacheProbe.release)
        assert await asyncio.wait_for(previous.result(), 20) == prior
        await select_current(client, deployment, "plugin-0-1-0")
        reverted = await client.start_workflow(LegacyCacheProbe.run, "same", id=f"rolled-{uuid4()}",
                                               task_queue=rig.queue, execution_timeout=timedelta(seconds=90))
        rollback_new = await query_until(reverted, LegacyCacheProbe.observations)
        assert rollback_new[0] == rollback_new[1]
        await upgraded.signal(LegacyCacheProbe.release)
        assert await asyncio.wait_for(upgraded.result(), 20) == latest
        await reverted.signal(LegacyCacheProbe.release)
        assert await asyncio.wait_for(reverted.result(), 20) == rollback_new
        old_history, new_history, rollback_history = await asyncio.gather(
            previous.fetch_history(), upgraded.fetch_history(), reverted.fetch_history(),
        )
        assert builds(old_history) == builds(rollback_history) == ["plugin-0-1-0"]
        assert builds(new_history) == ["plugin-1-0-0"]
        old_path = persist(old_history, "AT10-old", rig.root)
        new_path = persist(new_history, "AT10-new", rig.root)
        assert legacy_replay(rig, previous.id, old_path)["failure"] is None
        assert (await replay("version", upgraded.id, new_path)).replay_failure is None
        leading = (await replay("version", previous.id, old_path)).replay_failure
        back = legacy_replay(rig, upgraded.id, new_path)
        rename = (await replay("version", upgraded.id, new_path, rename=True)).replay_failure
        assert leading is not None and "nondetermin" in type(leading).__name__.lower()
        assert back["failure"] is not None and "nondetermin" in back["failure"].lower()
        assert rename is not None and "nondetermin" in type(rename).__name__.lower()
        evidence("AT10", {"worker_builds": [builds(h) for h in (old_history, new_history, rollback_history)],
                          "activity_counts": [len(activities_in(h)) for h in (old_history, new_history)],
                          "same_version": "passed", "forward_in_place": type(leading).__name__,
                          "rollback_in_place": back["failure"], "node_rename": type(rename).__name__})

    asyncio.run(run())
