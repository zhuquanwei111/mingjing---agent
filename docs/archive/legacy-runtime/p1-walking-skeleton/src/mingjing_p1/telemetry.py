"""Local synthetic trace sink. Business audit writes use PostgreSQL."""

import json
import os
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from temporalio.contrib.opentelemetry import TracingInterceptor


class FileSink(SpanExporter):
    def __init__(self, path: Path, fail: bool):
        self.path = path
        self.fail = fail

    def export(self, spans: tuple[ReadableSpan, ...]) -> SpanExportResult:
        with self.path.open("a", encoding="utf-8") as stream:
            for span in spans:
                stream.write(json.dumps({
                    "name": span.name,
                    "trace_id": f"{span.get_span_context().trace_id:032x}",
                    "attrs": dict(span.attributes or {}),
                    "exported": not self.fail,
                }) + "\n")
        return SpanExportResult.FAILURE if self.fail else SpanExportResult.SUCCESS


def configure() -> None:
    path = os.environ.get("MINGJING_TRACE_FILE")
    if path is None:
        return
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(FileSink(
        Path(path), os.environ.get("MINGJING_TRACE_FAIL") == "1",
    )))
    trace.set_tracer_provider(provider)


def tracer() -> trace.Tracer:
    return trace.get_tracer("mingjing.p1")


def interceptor() -> TracingInterceptor:
    return TracingInterceptor(tracer())
