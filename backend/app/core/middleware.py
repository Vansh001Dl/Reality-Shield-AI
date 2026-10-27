from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client sliding-window limiter (shared across routes in one worker)."""
    def __init__(self, app, requests_per_window=1000, window_seconds=60):
        super().__init__(app)
        self.limit = max(1, requests_per_window)
        self.window = max(1, window_seconds)
        self.hits = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request, call_next):
        if request.url.path in {"/health", "/ready", "/metrics", "/api/v1/metrics"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = monotonic()
        with self.lock:
            bucket = self.hits[client]
            while bucket and now - bucket[0] >= self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, self.window - int(now - bucket[0]))
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429,
                                    headers={"Retry-After": str(retry_after)})
            bucket.append(now)
        return await call_next(request)
