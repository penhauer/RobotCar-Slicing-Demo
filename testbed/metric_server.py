#!/usr/bin/env python3
"""
Simple metric ingestion server that accepts POSTed JSON ping events and
exposes Prometheus metrics on /metrics.

POST path (configurable via METRIC_INGEST_PATH):
  - expects JSON object:
      {"type":"ping_rtt", "target":"ping.example.com", "rtt_ms": 12.3, "ts_ms": 159...}
  - accepts newline-delimited JSON as well.

Environment:
  METRIC_HOST           host to bind (default 0.0.0.0)
  METRIC_PORT           port to bind (default 8003)
  METRIC_INGEST_PATH    path to receive POSTs (default /ingest)
  METRIC_LABEL_NAME     additional label name to attach to received metrics (default "source")
  METRIC_LABEL_VALUE    default value for the above label if not provided in the incoming event
"""
import os
import io
import json
import time
import logging
from wsgiref.simple_server import make_server
from typing import Iterable

from prometheus_client import make_wsgi_app, Gauge, Histogram, Counter

LOG = logging.getLogger("metric_server")
logging.basicConfig(level=logging.INFO)

METRIC_HOST = os.getenv("METRIC_HOST", "0.0.0.0")
METRIC_PORT = int(os.getenv("METRIC_PORT", "8003"))
METRIC_INGEST_PATH = os.getenv("METRIC_INGEST_PATH", "/ingest")

# Additional label configuration: name and default value
METRIC_LABEL_NAME = os.getenv("METRIC_LABEL_NAME", "source").strip()
METRIC_LABEL_VALUE = os.getenv("METRIC_LABEL_VALUE", "").strip()

# Ensure label name is a valid non-empty string
if not METRIC_LABEL_NAME:
    METRIC_LABEL_NAME = "source"

LABEL_NAMES = ("target", METRIC_LABEL_NAME)

# Prometheus metrics (include the configured label name)
PING_RTT_GAUGE = Gauge("ping_rtt_ms", "Latest ping RTT in milliseconds", LABEL_NAMES)
PING_RTT_HIST = Histogram(
    "ping_rtt_ms_hist",
    "Ping RTT distribution in milliseconds",
    LABEL_NAMES,
    buckets=(0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, float("inf")),
)
PING_FAIL_COUNTER = Counter("ping_fail_total", "Count of failed/timeout pings", LABEL_NAMES)
PING_LAST_SEEN = Gauge("ping_last_seen_timestamp_seconds", "Last seen timestamp (epoch seconds)", LABEL_NAMES)
INGEST_COUNT = Counter("metric_ingest_requests_total", "Number of ingest POSTs received")

_wsgi_metrics_app = make_wsgi_app()


def _iter_lines_to_jsons(b: bytes) -> Iterable[dict]:
    """
    Parse either a single JSON object, a JSON array, or newline-delimited JSON objects.
    Yields dicts.
    """
    text = b.decode("utf-8", errors="replace").strip()
    if not text:
        return
    # Try single JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    yield item
        elif isinstance(obj, dict):
            yield obj
        return
    except Exception:
        # fallthrough to newline-delimited parsing
        pass

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj
        except Exception:
            LOG.warning("Failed to parse line as JSON: %r", line)


def _handle_ping_event(ev: dict):
    """
    Process a single ping event dictionary and update metrics.
    Expected keys: type, target, rtt_ms, ts_ms
    An additional label (configured by METRIC_LABEL_NAME) is read from the event
    or filled from METRIC_LABEL_VALUE when missing.
    """
    t = ev.get("type", "")
    if t != "ping_rtt":
        LOG.debug("Ignoring non-ping event type: %r", t)
        return

    target = ev.get("target") or "unknown"
    # label value: prefer event-provided value, else env default, else "unknown"
    label_val = ev.get(METRIC_LABEL_NAME)
    if label_val is None:
        label_val = METRIC_LABEL_VALUE or "unknown"

    # Update last seen
    now = time.time()
    try:
        PING_LAST_SEEN.labels(target=target, **{METRIC_LABEL_NAME: label_val}).set(now)
    except Exception:
        pass

    rtt = ev.get("rtt_ms")
    if rtt is None:
        # treated as failed/timeout ping
        try:
            PING_FAIL_COUNTER.labels(target=target, **{METRIC_LABEL_NAME: label_val}).inc()
        except Exception:
            pass
        LOG.debug("Ping failed for %s (%s=%s)", target, METRIC_LABEL_NAME, label_val)
        return

    try:
        # ensure numeric
        rtt_val = float(rtt)
    except Exception:
        LOG.warning("Non-numeric rtt_ms received: %r", rtt)
        try:
            PING_FAIL_COUNTER.labels(target=target, **{METRIC_LABEL_NAME: label_val}).inc()
        except Exception:
            pass
        return

    try:
        PING_RTT_GAUGE.labels(target=target, **{METRIC_LABEL_NAME: label_val}).set(rtt_val)
        PING_RTT_HIST.labels(target=target, **{METRIC_LABEL_NAME: label_val}).observe(rtt_val)
    except Exception:
        LOG.exception("Failed updating metrics for %s (%s=%s) rtt=%r", target, METRIC_LABEL_NAME, label_val, rtt_val)
        return

    LOG.debug("Recorded ping %s (%s=%s) -> %sms", target, METRIC_LABEL_NAME, label_val, rtt_val)


def application(environ, start_response):
    """
    WSGI routing: /metrics -> prometheus app, /ingest -> handle POST ingest,
    other paths -> 404.
    """
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path == METRIC_INGEST_PATH:
        if method != "POST":
            start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
            return [b"Method Not Allowed\n"]

        try:
            INGEST_COUNT.inc()
            length = int(environ.get("CONTENT_LENGTH") or 0)
            body = environ["wsgi.input"].read(length) if length > 0 else environ["wsgi.input"].read()
            # Accept empty body
            if not body:
                start_response("400 Bad Request", [("Content-Type", "text/plain")])
                return [b"empty body\n"]

            for ev in _iter_lines_to_jsons(body):
                try:
                    _handle_ping_event(ev)
                except Exception:
                    LOG.exception("Error handling event: %r", ev)

            start_response("200 OK", [("Content-Type", "application/json")])
            return [b'{"status":"ok"}\n']
        except Exception:
            LOG.exception("Failed to handle ingest request")
            start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
            return [b"internal error\n"]

    if path == "/metrics":
        return _wsgi_metrics_app(environ, start_response)

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"not found\n"]


def run_server(host: str = METRIC_HOST, port: int = METRIC_PORT):
    LOG.info(
        "Starting metric server on http://%s:%d (ingest=%s, metrics=/metrics) label=%s",
        host,
        port,
        METRIC_INGEST_PATH,
        METRIC_LABEL_NAME,
    )
    with make_server(host, port, application) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            LOG.info("Shutting down metric server")


if __name__ == "__main__":
    run_server()