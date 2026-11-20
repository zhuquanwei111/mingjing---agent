import argparse
import asyncio
import getpass
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from .artifacts import BlobStore
from .catalog import Catalog
from .db import Database
from .examples import builtins
from .http_api import API, serve
from .service import Service
from .temporal_adapter import TemporalAdapter, connect, deployment_from_environment, make_worker


def service() -> Service:
    db = Database(os.environ["MINGJING_DB_DSN"])
    catalog = Catalog(db, os.environ["MINGJING_ENVIRONMENT"], builtins(db))
    return Service(db, catalog, BlobStore(Path(os.environ["MINGJING_BLOBS"])))


def telemetry() -> None:
    if os.environ.get("MINGJING_LOCAL_TRACE") == "1":
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)


async def worker(runtime: Service, queue: str) -> None:
    client = await connect()
    await make_worker(client, queue, runtime, deployment_from_environment()).run()


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    migration = commands.add_parser("migrate")
    migration.add_argument("--directory", type=Path, default=Path("migrations"))
    bootstrap = commands.add_parser("add-identity")
    bootstrap.add_argument("tenant")
    bootstrap.add_argument("subject")
    bootstrap.add_argument("--administrator", action="store_true")
    commands.add_parser("api")
    commands.add_parser("worker")
    options = parser.parse_args()
    if options.command == "migrate":
        applied = Database(os.environ["MINGJING_MIGRATION_DSN"]).migrate(options.directory)
        print("Applied migrations:", ", ".join(applied) if applied else "none")
    elif options.command == "add-identity":
        if not sys.stdin.isatty():
            parser.error("add-identity needs a trusted interactive terminal")
        Database(os.environ["MINGJING_MIGRATION_DSN"]).add_identity(
            options.tenant, options.subject, getpass.getpass("Bearer token: "),
            datetime.now(UTC) + timedelta(hours=24), administrator=options.administrator,
        )
    else:
        telemetry()
        runtime = service()
        queue = os.environ["TEMPORAL_TASK_QUEUE"]
        if options.command == "worker":
            asyncio.run(worker(runtime, queue))
        else:
            serve(API(runtime, TemporalAdapter(runtime, queue)), "127.0.0.1",
                  int(os.environ.get("MINGJING_PORT", "8080")))


if __name__ == "__main__":
    main()
