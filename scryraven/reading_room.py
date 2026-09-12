"""Local HTTP shell over ResearchSession and SessionStore; no research decisions."""

from __future__ import annotations

import argparse
import secrets
from pathlib import Path
from threading import Lock
from time import monotonic

from flask import Flask, abort, redirect, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer
from markupsafe import Markup
from werkzeug.exceptions import HTTPException, SecurityError
from werkzeug.serving import WSGIRequestHandler, make_server

from scryraven.presentation import answer_html, source_body_html, source_label
from scryraven.session import ResearchSession
from scryraven.session_store import (
    SessionConflictError,
    SessionStore,
    SessionStoreError,
    SQLiteSessionStore,
)

_HOST = "127.0.0.1"
_PORT = 7331


class _FormError(Exception):
    def __init__(self, repeated=False):
        self.repeated = repeated


class _Forms:
    """Transient CSRF/replay protection, bound to the action and displayed revision.

    Nothing here is durable product state. Restarting expires open forms; reading
    and reopening sessions are unaffected. The lock protects concurrent POSTs.
    """

    lifetime = 24 * 60 * 60

    def __init__(self):
        self.signer = URLSafeTimedSerializer(secrets.token_urlsafe(32))
        self.used: dict[str, float] = {}
        self.lock = Lock()

    def issue(self, action, session_id="", revision=0):
        return self.signer.dumps([action, session_id, revision, secrets.token_urlsafe(20)])

    def claim(self, token, action, session_id=""):
        try:
            saved_action, saved_id, revision, _ = self.signer.loads(token, max_age=self.lifetime)
        except (BadSignature, ValueError, TypeError):
            raise _FormError() from None
        if (saved_action, saved_id) != (action, session_id) or type(revision) is not int or revision < 0:
            raise _FormError()
        with self.lock:
            now = monotonic()
            self.used = {key: when for key, when in self.used.items() if now - when < self.lifetime}
            if token in self.used:
                raise _FormError(repeated=True)
            self.used[token] = now
        return revision


def create_app(*, database: str | Path | None = None, store: SessionStore | None = None,
               session_options: dict | None = None) -> Flask:
    """Inject only the existing store and ResearchSession's ordinary I/O options."""
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=256 * 1024, TRUSTED_HOSTS=["127.0.0.1", "localhost"])
    custody = store if store is not None else SQLiteSessionStore(database)
    options = dict(session_options or {})
    forms = _Forms()

    @app.before_request
    def protect_local_requests():
        # Host validation also prevents DNS rebinding. Do not trust proxy headers.
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if (origin is not None and origin != request.host_url.rstrip("/")) or (
                request.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                abort(403)
            if request.mimetype != "application/x-www-form-urlencoded":
                abort(415)

    @app.after_request
    def response_safety(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"
        )
        # Browsers can send Origin: null on native POSTs under no-referrer.
        # Same-origin preserves our local Origin check; external links still
        # carry rel=noreferrer and disclose no local referrer.
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    def page(session_id=None, *, question="", error=None, status=200, confirmation=False, edit_title=False):
        try:
            history = custody.list_sessions()
            saved = custody.load(session_id) if session_id else None
        except SessionStoreError as exc:
            if exc.code == "session_not_found":
                return redirect(url_for("new_research", notice="missing"), 303)
            return render_template("reading_room.html", history=(), saved=None, turns=(),
                                   error="Saved research is unavailable. Please try reopening the Reading Room.",
                                   unavailable=True), 503
        turns = []
        for number, turn in enumerate(saved.state.turns if saved else (), 1):
            prefix = f"turn-{number}-source-"
            turns.append({
                "number": number, "question": turn.question, "posture": turn.posture,
                "answer": Markup(answer_html(turn, source_prefix=prefix)),
                "sources": [{"number": c.number, "id": prefix + str(c.number), "title": source_label(c),
                             "body": Markup(source_body_html(c, collapse_long=True))} for c in turn.citations],
            })
        metadata = saved.metadata if saved else None
        issue = lambda action: forms.issue(action, metadata.session_id if metadata else "",
                                           metadata.revision if metadata else 0)
        notice = {"missing": "That session is no longer available. Your other research is here.",
                  "deleted": "Session deleted.", "renamed": "Session renamed."}.get(request.args.get("notice"))
        return render_template(
            "reading_room.html", history=history, saved=saved, turns=turns, question=question,
            error=error, notice=notice, confirmation=confirmation, form_token=issue,
            renaming=bool(saved and (edit_title or request.args.get("edit") == "rename")),
        ), status

    @app.get("/")
    def new_research():
        return page()

    @app.get("/sessions/<session_id>")
    def open_session(session_id):
        return page(session_id)

    def claim(action, session_id=""):
        return forms.claim(request.form.get("form_token", ""), action, session_id)

    @app.post("/ask")
    @app.post("/sessions/<session_id>/ask")
    def ask(session_id=None):
        question = request.form.get("question", "").strip()
        try:
            revision = claim("ask", session_id or "")
        except _FormError as exc:
            message = ("This question was already submitted. Reopen the session from history to see any saved answer."
                       if exc.repeated else "This form has expired. Review your question and submit it again.")
            return page(session_id, question=question, error=message, status=409)
        if not question:
            return page(session_id, error="Write a research question to begin.", status=400)
        session = None
        try:
            session = (ResearchSession.open(session_id, store=custody, **options) if session_id
                       else ResearchSession.create(store=custody, **options))
            if session.metadata.revision != revision:
                raise SessionConflictError()
            session.ask(question)
        except Exception as exc:
            # There is no completed turn on failure. Remove only our own new,
            # still-empty session; the revision guard protects a concurrent writer.
            if not session_id and session is not None:
                try:
                    custody.delete(session.session_id, revision=0)
                except SessionStoreError:
                    pass
            if isinstance(exc, SessionStoreError) and exc.code == "session_not_found":
                return page(error="That session was deleted. Your question is kept below; you can start new research.",
                            question=question, status=409)
            if isinstance(exc, SessionConflictError):
                return page(session_id, question=question, status=409,
                            error="This session changed. Review the latest conversation before submitting again.")
            return page(session_id, question=question, status=503,
                        error="Research didn’t complete. ScryRaven stopped before an answer was saved. "
                              "Your existing conversation is unchanged. You can edit the question or try again.")
        return redirect(url_for("open_session", session_id=session.session_id,
                                _anchor=f"turn-{session.metadata.revision}"), 303)

    @app.post("/sessions/<session_id>/rename")
    def rename_session(session_id):
        claim("rename", session_id)
        try:
            custody.rename(session_id, request.form.get("title", ""))
        except SessionStoreError as exc:
            if exc.code == "invalid_session_title":
                return page(session_id, error="Please give this session a title before saving.", status=400, edit_title=True)
            raise
        return redirect(url_for("open_session", session_id=session_id, notice="renamed"), 303)

    @app.get("/sessions/<session_id>/delete")
    def confirm_delete(session_id):
        return page(session_id, confirmation=True)

    @app.post("/sessions/<session_id>/delete")
    def delete_session(session_id):
        revision = claim("delete", session_id)
        if request.form.get("confirm") != "delete":
            abort(400)
        custody.delete(session_id, revision=revision)
        return redirect(url_for("new_research", notice="deleted"), 303)

    @app.errorhandler(_FormError)
    def form_error(exc):
        return page(error="This action has expired or was already submitted. Please reopen the session and try again.",
                    status=409)

    @app.errorhandler(SessionStoreError)
    def store_error(exc):
        if exc.code == "session_not_found":
            return redirect(url_for("new_research", notice="missing"), 303)
        if isinstance(exc, SessionConflictError):
            return page(error="The session changed after you opened it. Reopen it before making this change.", status=409)
        return page(error="The change could not be saved. Please reopen the session and try again.", status=503)

    @app.errorhandler(Exception)
    def bounded_error(exc):
        # Neither HTTP input nor execution exceptions become public diagnostics.
        if isinstance(exc, SecurityError):
            # Host rejection happens before Flask creates a URL adapter.
            return ("<!doctype html><html lang=en><meta charset=utf-8><title>Reading Room</title>"
                    "<p>Open the local Reading Room address shown when you launched it.</p></html>"), 400
        status = exc.code if isinstance(exc, HTTPException) else 500
        return render_template("reading_room.html", history=(), saved=None, turns=(), unavailable=True,
                               error="This page or request is unavailable. Reopen the Reading Room to continue."), status

    return app


class _QuietHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        # Local paths, questions and request payloads are not an access log.
        pass


def serve(app: Flask, *, port: int = _PORT) -> None:
    """One local threaded HTTP server; each ask finishes in its HTTP request."""
    server = make_server(_HOST, port, app, threaded=True, request_handler=_QuietHandler)
    print(f"ScryRaven Reading Room: http://{_HOST}:{server.server_port}", flush=True)
    print("Open this address in your browser. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open ScryRaven’s local Reading Room.")
    parser.add_argument("--database", type=Path, metavar="PATH", help="Use a chosen session database location.")
    parser.add_argument("--port", type=int, default=_PORT, help=f"Local HTTP port (default: {_PORT}).")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    try:
        serve(create_app(database=args.database), port=args.port)
    except KeyboardInterrupt:
        pass
    except (OSError, SessionStoreError):
        print("The Reading Room could not start. Check the database location or choose another --port.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
