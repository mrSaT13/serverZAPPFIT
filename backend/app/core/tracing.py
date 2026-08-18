"""OpenTelemetry tracing setup for the FastAPI application."""

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _tracing_enabled() -> bool:
    """
    Return whether tracing is enabled by environment.

    Args:
        None.

    Returns:
        True when tracing should be configured.

    Raises:
        None.
    """
    return os.environ.get("JAEGER_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }


def setup_tracing(app: FastAPI) -> None:
    """
    Configure OpenTelemetry tracing for FastAPI.

    Args:
        app: FastAPI application to instrument.

    Returns:
        None.

    Raises:
        None.
    """
    if not _tracing_enabled():
        return

    endpoint = (
        f"{os.environ.get('JAEGER_PROTOCOL', 'http')}://"
        f"{os.environ.get('JAEGER_HOST', 'jaeger')}:"
        f"{os.environ.get('JAEGER_PORT', '4317')}"
    )
    resource = Resource.create({"service.name": "backend_api"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    FastAPIInstrumentor.instrument_app(app)
