import asyncio
from uuid import uuid4

from mingjing_p1.temporal.smoke import connect, make_worker, run_smoke


def test_pinned_temporal_cli_smoke() -> None:
    async def run() -> None:
        client = await connect()
        queue = f"p1-cli-smoke-{uuid4()}"
        async with make_worker(client, queue):
            results = await run_smoke(client, queue)
        print(results)
        assert list(results) == ["SmokePlain", "SmokeGraph", "SmokeFunctional"]
        assert set(results.values()) == {"synthetic:p1-smoke"}

    asyncio.run(run())
