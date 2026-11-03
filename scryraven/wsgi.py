"""Single-process production entrypoint: ``python -m scryraven.wsgi``."""

from __future__ import annotations

import atexit
import os
import sys

from scryraven.hosted import HostedConfig, HostedConfigurationError
from scryraven.model import ModelError, OpenAIModel


def create_application(*, config: HostedConfig | None = None, session_options=None, **kwargs):
    from scryraven.reading_room import create_app

    config = HostedConfig.from_env() if config is None else config
    model = OpenAIModel(config.run_settings.model_config(), backend="api")
    model.validate_configuration()  # Presence and syntax only; no provider request.
    options = dict(session_options or {})
    options["model"] = model
    app = create_app(database=config.database, hosted=config, session_options=options, **kwargs)
    manager = app.extensions.get("research_jobs")
    if manager is None:
        raise HostedConfigurationError()
    diagnostics = app.extensions["hosted_diagnostics"]
    diagnostics.start_maintenance()
    atexit.register(manager.shutdown)
    atexit.register(diagnostics.close)
    return app


def main() -> int:
    from waitress import serve

    try:
        port = int(os.environ.get("PORT", "8080"))
        threads = int(os.environ.get("SCRYRAVEN_HTTP_THREADS", "8"))
        host = os.environ.get("SCRYRAVEN_BIND_HOST", "0.0.0.0")
        if not 1 <= port <= 65535 or not 4 <= threads <= 32 or host not in {"0.0.0.0", "127.0.0.1", "::"}:
            raise HostedConfigurationError()
        app = create_application()
    except (HostedConfigurationError, ModelError, OSError, ValueError):
        print("Hosted Reading Room could not start: check the explicit hosted configuration and volume.",
              file=sys.stderr, flush=True)
        return 1
    try:
        # No forwarding headers are trusted. The application uses its configured
        # HTTPS origin for CSRF checks, so spoofed proxy metadata has no authority.
        serve(app, host=host, port=port, threads=threads,
              clear_untrusted_proxy_headers=True, ident="ScryRaven",
              url_scheme="https", expose_tracebacks=False)
    finally:
        try:
            app.extensions["research_jobs"].shutdown()
        finally:
            app.extensions["hosted_diagnostics"].close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
