"""
Non-secret private broker sketch for AG-96I3D0 operators.

Do not run this file from the repository as-is. Copy the shape into a private
local location, replace placeholders there, and keep one-shot tokens plus
provider configuration outside the repo.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

HOST = "127.0.0.1"
PORT = 8765
MAX_RUNS = 1
ALLOWLISTED_JOBS = {
    "ag96i3d0-official-current-once": {
        "max_provider_search_calls": 1,
        "max_fetch_read_attempts": 0,
        "max_model_calls": 0,
        "retries_allowed": False,
    }
}


class PrivateBrokerHandler(BaseHTTPRequestHandler):
    runs_remaining: ClassVar[int] = MAX_RUNS
    one_shot_token: ClassVar[str] = "replace-in-private-copy"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/run":
            self._send_json(404, {"error": "not_found"})
            return
        if self.headers.get("X-ScryRaven-Broker-Token") != self.one_shot_token:
            self._send_json(403, {"error": "invalid_token"})
            return
        if self.runs_remaining <= 0:
            self._send_json(403, {"error": "max_runs_exhausted"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        job_id = payload.get("job_id")
        if payload.get("confirm_live") is not True:
            self._send_json(400, {"error": "missing_live_confirmation"})
            return
        if job_id not in ALLOWLISTED_JOBS:
            self._send_json(400, {"error": "unknown_job_id", "job_id": job_id})
            return

        self.runs_remaining -= 1
        self._send_json(
            200,
            {
                "status": "template_only",
                "job_id": job_id,
                "budget": ALLOWLISTED_JOBS[job_id],
                "sanitized_output_path": "output/ag96i3d0_broker_response.json",
            },
        )

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PrivateBrokerHandler)
    print(f"template broker listening on http://{HOST}:{PORT}/run")
    server.serve_forever()


if __name__ == "__main__":
    main()
