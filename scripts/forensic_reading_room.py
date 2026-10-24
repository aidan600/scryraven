"""Credentialed forensic child over the ordinary Reading Room application.

The existing command doorman alone loads the environment file. This entrypoint
only checks configuration presence and explicitly selects the plan transport;
it never opens credentials or the plan authentication vault during startup.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from scryraven import reading_room
from scryraven.model import OpenAIModel
from scryraven.session_store import SQLiteSessionStore


def _write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-directory", required=True, type=Path)
    args = parser.parse_args(argv)
    run = args.run_directory.resolve()
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest.update(launch_status="starting", server_pid=os.getpid(), safe_error_code=None)
    # Removing the API key is defense in depth. The explicit backend itself has
    # no API fallback, even when the brokered environment contains an API key.
    os.environ.pop("OPENAI_API_KEY", None)
    configured = {
        provider: bool(os.environ.get(name, "").strip())
        for provider, name in (("exa", "EXA_API_KEY"), ("serper", "SERPER_API_KEY"),
                               ("linkup", "LINKUP_API_KEY"))
    }
    manifest["acquisition_configuration"] = configured
    failure_code = "forensic_launch_failed"
    try:
        if not configured["exa"]:
            failure_code = "exa_configuration_missing"
            raise ValueError(failure_code)
        failure_code = "chatgpt_plan_backend_unavailable"
        model = OpenAIModel(backend="chatgpt_plan", plan_account="personal")
        if (model.backend != "chatgpt_plan" or model.plan_transport is None
                or model.plan_transport.account != "personal"):
            raise ValueError(failure_code)
        manifest.update(
            inference_backend=model.backend, plan_account=model.plan_transport.account,
            api_inference_fallback=False, model_profile=asdict(model.config),
            startup_model_dispatches=model.plan_transport.physical_requests,
        )
        failure_code = "forensic_checkout_unavailable"
        repository = Path(__file__).resolve().parents[1]
        manifest["repository_path"] = str(repository)
        manifest["git_sha"] = subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        failure_code = "forensic_server_start_failed"
        store = SQLiteSessionStore(run / "sessions.sqlite3")
        store.list_sessions()  # Retain an initialized, isolated database even before a first ask.
        app = reading_room.create_app(
            store=store, session_options={"model": model},
            dogfood_log=run / "turns.jsonl", forensic_log=run / "observer.jsonl",
        )

        def ready(port: int) -> None:
            manifest.update(launch_status="ready", port=port,
                            ready_at_utc=datetime.now(timezone.utc).isoformat())
            _write_manifest(manifest_path, manifest)

        reading_room.serve(app, port=manifest["port"], on_ready=ready)
    except KeyboardInterrupt:
        pass
    except (Exception, SystemExit):
        # Never publish an arbitrary exception or private environment value.
        manifest.update(launch_status="failed", safe_error_code=failure_code)
        _write_manifest(manifest_path, manifest)
        print(f"Forensic Reading Room could not start: {failure_code}", flush=True)
        return 2
    manifest["launch_status"] = "stopped"
    _write_manifest(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
