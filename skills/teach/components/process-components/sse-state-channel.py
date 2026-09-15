"""Flask SSE template for versioned teaching-workspace state refreshes."""

import json
import threading

from flask import Response, request, stream_with_context


state_condition = threading.Condition()
state_version = 0


def notify_state_change():
    """Call only after the corresponding database transaction commits."""
    global state_version
    with state_condition:
        state_version += 1
        state_condition.notify_all()


def register_sse_route(app):
    @app.get("/api/events")
    def api_events():
        try:
            seen_version = int(request.args.get("version", 0))
        except ValueError:
            seen_version = 0

        @stream_with_context
        def event_stream():
            nonlocal seen_version
            while True:
                with state_condition:
                    state_condition.wait_for(
                        lambda: state_version > seen_version,
                        timeout=20,
                    )
                    current_version = state_version
                if current_version > seen_version:
                    seen_version = current_version
                    payload = json.dumps({"version": current_version})
                    yield f"event: state\ndata: {payload}\n\n"
                else:
                    yield ": keepalive\n\n"

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
