"""Serve disposable synthetic answers for a private-LAN iPhone print check."""

from __future__ import annotations

import argparse
import sys
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_reading_room_print_browser import EARLY, make_print_fixture
from werkzeug.serving import make_server
from werkzeug.wrappers import Response

from scryraven.reading_room import _QuietHandler


def private_host(value):
    try:
        address = IPv4Address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use 127.0.0.1 or a private LAN IPv4 address.") from exc
    if address != IPv4Address("127.0.0.1") and not any(address in network for network in (
        IPv4Network("10.0.0.0/8"), IPv4Network("172.16.0.0/12"), IPv4Network("192.168.0.0/16"),
    )):
        raise argparse.ArgumentTypeError("Use 127.0.0.1 or a private LAN IPv4 address.")
    return str(address)


def read_only(app):
    def serve(environ, start_response):
        if environ["REQUEST_METHOD"] not in {"GET", "HEAD"}:
            return Response("Synthetic fixture is read-only.\n", status=405,
                            headers={"Allow": "GET, HEAD", "Cache-Control": "no-store"})(environ, start_response)
        return app(environ, start_response)

    return serve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=private_host, default="127.0.0.1",
                        help="Bind only this private LAN IPv4 address (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=7332)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Use a port from 1 to 65535.")

    with TemporaryDirectory(prefix="scryraven-print-") as directory, patch(
        "scryraven.dictation.available", return_value=False,
    ):
        origin = f"http://{args.host}:{args.port}"
        app, path = make_print_fixture(Path(directory) / "print.sqlite3", source_urls=(
            origin + "/synthetic/canopy-survey", origin + "/synthetic/design-notes",
        ))
        app.config["TRUSTED_HOSTS"] = [args.host]

        @app.get("/synthetic/canopy-survey")
        def canopy_survey():
            return Response("Synthetic print-test source only.\n\n" + EARLY + "\n", mimetype="text/plain")

        @app.get("/synthetic/design-notes")
        def design_notes():
            return Response("Synthetic print-test source only.\n\nSynthetic design notes for shade at bus stops.\n",
                            mimetype="text/plain")

        server = None
        try:
            server = make_server(args.host, args.port, read_only(app), threaded=True, request_handler=_QuietHandler)
            print("Synthetic answers only; provider calls and all mutations are disabled.", flush=True)
            print(f"Synthetic Reading Room: http://{args.host}:{server.server_port}{path}#turn-2", flush=True)
            print("Press Ctrl+C to stop and remove the temporary fixture.", flush=True)
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if server is not None:
                server.server_close()
            app.extensions["research_jobs"].shutdown()


if __name__ == "__main__":
    main()
