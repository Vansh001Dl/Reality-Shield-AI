"""Prometheus HTTP metrics, with a small fallback for an uninstalled checkout."""
try:
    from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest
    REQUEST_COUNT = Counter("realityshield_http_requests_total", "HTTP requests", ["method", "path", "status"])
    REQUEST_LATENCY = Histogram("realityshield_http_request_duration_seconds", "HTTP request duration", ["method", "path"])
except ImportError:
    from collections import defaultdict
    from threading import Lock

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    _counts, _latencies, _lock = defaultdict(int), defaultdict(list), Lock()

    class _Metric:
        def __init__(self, storage):
            self.storage = storage
        def labels(self, *labels):
            key = tuple(labels)
            class Sample:
                def inc(inner, amount=1):
                    with _lock:
                        self.storage[key] += amount
                def observe(inner, value):
                    with _lock:
                        self.storage[key].append(value)
            return Sample()

    REQUEST_COUNT = _Metric(_counts)
    REQUEST_LATENCY = _Metric(_latencies)

    def generate_latest():
        rows = ["# HELP realityshield_http_requests_total HTTP requests",
                "# TYPE realityshield_http_requests_total counter"]
        rows.extend(f'realityshield_http_requests_total{{method="{m}",path="{p}",status="{s}"}} {n}'
                    for (m, p, s), n in _counts.items())
        rows.extend(f'realityshield_http_request_duration_seconds_count{{method="{m}",path="{p}"}} {len(v)}'
                    for (m, p), v in _latencies.items())
        return ("\n".join(rows) + "\n").encode()
