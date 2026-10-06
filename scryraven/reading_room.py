"""Local HTTP shell over ResearchSession and SessionStore; no research decisions."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from threading import Lock
from time import monotonic

from flask import Flask, Response, abort, redirect, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer
from markupsafe import Markup
from werkzeug.exceptions import HTTPException, SecurityError
from werkzeug.serving import WSGIRequestHandler, make_server

from scryraven.documents import (
    ALREADY_ATTACHED_NOTICE,
    DOCUMENT_ERROR_MESSAGES,
    DOCUMENT_ID,
    MAX_PDF_BYTES,
    TEXT_ONLY_WARNING,
    DocumentRejected,
    content_disposition,
    textless_page_warning,
)
from scryraven.dogfood_diagnostics import DogfoodLog, TurnDiagnostics
from scryraven.forensic_log import ForensicLog
from scryraven.presentation import answer_html, source_body_html, source_free_supported, source_label
from scryraven.session import ResearchSession
from scryraven.session_store import (
    SessionConflictError,
    SessionStore,
    SessionStoreError,
    SQLiteSessionStore,
)

_HOST = "127.0.0.1"
_PORT = 7331
_FORM_BODY_BYTES = 256 * 1024
_PDF_UPLOADS = {"attach_new_document", "attach_session_document"}


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
               session_options: dict | None = None,
               dogfood_log: str | Path | None = None,
               forensic_log: str | Path | None = None) -> Flask:
    """Inject only the existing store and ResearchSession's ordinary I/O options."""
    app = Flask(__name__)
    # Ordinary forms keep the 256 KiB bound below. Only the PDF routes may use the
    # larger ceiling, and they still reject anything past MAX_PDF_BYTES.
    app.config.update(MAX_CONTENT_LENGTH=MAX_PDF_BYTES, MAX_FORM_MEMORY_SIZE=MAX_PDF_BYTES,
                      TRUSTED_HOSTS=["127.0.0.1", "localhost"])
    custody = store if store is not None else SQLiteSessionStore(database)
    options = dict(session_options or {})
    session_path = custody.path if isinstance(custody, SQLiteSessionStore) else None
    diagnostic_path = Path(dogfood_log).expanduser().resolve() if dogfood_log is not None else None
    forensic_path = Path(forensic_log).expanduser().resolve() if forensic_log is not None else None

    def aliases(first: Path | None, second: Path | None) -> bool:
        return (first is not None and second is not None
                and (first == second or (first.exists() and second.exists()
                                         and first.samefile(second))))

    # Reject aliases before either JSONL target is opened. This includes paths
    # that resolve through symlinks and existing files joined by a hard link.
    if aliases(diagnostic_path, session_path):
        raise OSError("dogfood_log_matches_session_database")
    if aliases(forensic_path, session_path):
        raise OSError("forensic_log_matches_session_database")
    if aliases(forensic_path, diagnostic_path):
        raise OSError("forensic_log_matches_dogfood_log")
    diagnostics = (DogfoodLog(diagnostic_path, session_database=session_path)
                   if diagnostic_path is not None else None)
    forensics = (ForensicLog(forensic_path, session_database=session_path,
                            dogfood_log=diagnostic_path)
                 if forensic_path is not None else None)
    forms = _Forms()

    @app.before_request
    def protect_local_requests():
        # Host validation also prevents DNS rebinding. Do not trust proxy headers.
        upload = request.endpoint in _PDF_UPLOADS
        limit = MAX_PDF_BYTES if upload else _FORM_BODY_BYTES
        # Ordinary forms stay at 256 KiB even when the PDF ceiling is configured
        # for the two upload routes. This also bounds a body without Content-Length.
        request.max_content_length = limit
        request.max_form_memory_size = limit
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if (origin is not None and origin != request.host_url.rstrip("/")) or (
                request.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                abort(403)
            if request.mimetype != ("multipart/form-data" if upload else "application/x-www-form-urlencoded"):
                abort(415)
            if request.content_length is not None and request.content_length > limit:
                abort(413)

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
            return render_template("reading_room.html", history=(), saved=None, turns=(), documents=(),
                                   text_only_warning=TEXT_ONLY_WARNING,
                                   error="Saved research is unavailable. Please try reopening the Reading Room.",
                                   unavailable=True), 503
        metadata = saved.metadata if saved else None
        documents = []
        if saved:
            for document in saved.documents:
                documents.append({
                    "filename": document.filename, "pages": document.page_count,
                    "textless": textless_page_warning(document.textless_page_count),
                    "href": url_for("original_pdf", session_id=metadata.session_id,
                                    document_id=document.document_id),
                })
        turns = []
        for number, turn in enumerate(saved.state.turns if saved else (), 1):
            prefix = f"turn-{number}-source-"
            turns.append({
                "number": number, "question": turn.question, "posture": turn.posture,
                "operating_bound": turn.stop_reason == "research_bound",
                "source_free": source_free_supported(turn),
                "answer": Markup(answer_html(turn, source_prefix=prefix)),
                "sources": [{"number": c.number, "id": prefix + str(c.number), "title": source_label(c),
                             "body": Markup(source_body_html(
                                 c, collapse_long=True,
                                 original_href=(url_for("original_pdf", session_id=metadata.session_id,
                                                        document_id=c.document_id)
                                                if c.source_kind == "user_document" and c.document_id else None),
                             ))} for c in turn.citations],
            })
        issue = lambda action: forms.issue(action, metadata.session_id if metadata else "",
                                           metadata.revision if metadata else 0)
        notice = {"missing": "That session is no longer available. Your other research is here.",
                  "deleted": "Session deleted.", "renamed": "Session renamed.",
                  "already_attached": ALREADY_ATTACHED_NOTICE}.get(request.args.get("notice"))
        return render_template(
            "reading_room.html", history=history, saved=saved, turns=turns, documents=documents,
            text_only_warning=TEXT_ONLY_WARNING, question=question,
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
        result = None
        failure = None
        turn_diagnostics = TurnDiagnostics(started_at=monotonic(), clock=monotonic) if diagnostics else None
        turn_options = options
        if turn_diagnostics is not None or forensics is not None:
            turn_options = dict(options)
            prior_observer = turn_options.get("observe")

            def observe(event):
                # Optional sinks see the engine's observer copy. A logger failure
                # cannot affect the engine or the durable session commit.
                if turn_diagnostics is not None:
                    try:
                        turn_diagnostics.observe(event)
                    except Exception:
                        pass
                if forensics is not None:
                    try:
                        forensics.append(event, session_id=(session.session_id if session else session_id),
                                         revision_before=revision)
                    except Exception:
                        try:
                            forensics.disable()
                        except Exception:
                            pass
                if prior_observer is not None:
                    try:
                        prior_observer(event)
                    except Exception:
                        pass

            turn_options["observe"] = observe
        try:
            session = (ResearchSession.open(session_id, store=custody, **turn_options) if session_id
                       else ResearchSession.create(store=custody, **turn_options))
            if session.metadata.revision != revision:
                raise SessionConflictError()
            result = session.ask(question)
        except Exception as exc:
            failure = exc
            # There is no completed turn on failure. Remove only our own new,
            # still-empty session; the revision guard protects a concurrent writer.
            if not session_id and session is not None:
                try:
                    custody.delete(session.session_id, revision=0)
                except SessionStoreError:
                    pass
            if isinstance(exc, SessionStoreError) and exc.code == "session_not_found":
                response = page(error="That session was deleted. Your question is kept below; you can start new research.",
                                question=question, status=409)
            elif isinstance(exc, SessionConflictError):
                response = page(session_id, question=question, status=409,
                                error="This session changed. Review the latest conversation before submitting again.")
            else:
                response = page(session_id, question=question, status=503,
                                error="Research didn’t complete. ScryRaven stopped before an answer was saved. "
                                      "Your existing conversation is unchanged. You can edit the question or try again.")
        else:
            response = redirect(url_for("open_session", session_id=session.session_id,
                                    _anchor=f"turn-{session.metadata.revision}"), 303)
        if turn_diagnostics is not None:
            try:
                diagnostics.append(turn_diagnostics.record(
                    session_id=session.session_id if session is not None else session_id,
                    revision_before=revision,
                    revision_after=session.metadata.revision if failure is None else None,
                    result=result, error=failure,
                ))
            except Exception:
                # The committed turn and redirect have already been chosen.
                print("Reading Room dogfood diagnostics stopped: the local log could not be written.",
                      file=sys.stderr, flush=True)
        return response

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
        return render_template("reading_room.html", history=(), saved=None, turns=(), documents=(),
                               text_only_warning=TEXT_ONLY_WARNING, unavailable=True,
                               error="This page or request is unavailable. Reopen the Reading Room to continue."), status

    def upload_error(exc: DocumentRejected):
        return DOCUMENT_ERROR_MESSAGES.get(exc.code, DOCUMENT_ERROR_MESSAGES["pdf_malformed"])

    def read_upload() -> tuple[str, str, bytes]:
        storage = request.files.get("pdf")
        if storage is None:
            raise DocumentRejected("pdf_required")
        filename = storage.filename or ""
        media_type = storage.mimetype or ""
        try:
            data = storage.read(MAX_PDF_BYTES + 1)
        finally:
            storage.close()
        if len(data) > MAX_PDF_BYTES:
            raise DocumentRejected("pdf_too_large")
        return filename, media_type, data

    @app.post("/documents")
    def attach_new_document():
        try:
            revision = claim("attach", "")
        except _FormError as exc:
            message = ("This PDF was already submitted. Reopen the session from history if it was saved."
                       if exc.repeated else "This form has expired. Choose the PDF and submit it again.")
            return page(error=message, status=409)
        if revision != 0:
            return page(error="This form has expired. Choose the PDF and submit it again.", status=409)
        try:
            filename, media_type, data = read_upload()
        except DocumentRejected as exc:
            return page(error=upload_error(exc), status=400)
        session = custody.create()
        try:
            attached = custody.attach_document(session.metadata.session_id, 0, filename, media_type, data)
        except DocumentRejected as exc:
            try:
                custody.delete(session.metadata.session_id, revision=0)
            except SessionStoreError:
                pass
            return page(error=upload_error(exc), status=400)
        except Exception:
            try:
                custody.delete(session.metadata.session_id, revision=0)
            except SessionStoreError:
                pass
            raise
        target = {"session_id": session.metadata.session_id}
        if not attached.created:
            target["notice"] = "already_attached"
        return redirect(url_for("open_session", **target), 303)

    @app.post("/sessions/<session_id>/documents")
    def attach_session_document(session_id):
        try:
            revision = claim("attach", session_id)
        except _FormError as exc:
            message = ("This PDF was already submitted. Reopen the session from history if it was saved."
                       if exc.repeated else "This form has expired. Choose the PDF and submit it again.")
            return page(session_id, error=message, status=409)
        try:
            filename, media_type, data = read_upload()
            attached = custody.attach_document(session_id, revision, filename, media_type, data)
        except DocumentRejected as exc:
            return page(session_id, error=upload_error(exc), status=400)
        target = {"session_id": session_id}
        if not attached.created:
            target["notice"] = "already_attached"
        return redirect(url_for("open_session", **target), 303)

    @app.get("/sessions/<session_id>/documents/<document_id>/original")
    def original_pdf(session_id, document_id):
        if not DOCUMENT_ID.fullmatch(document_id or ""):
            abort(404)
        try:
            saved = custody.load(session_id)
        except SessionStoreError as exc:
            if exc.code == "session_not_found":
                abort(404)
            raise
        document = next((item for item in saved.documents if item.document_id == document_id), None)
        if document is None:
            abort(404)
        response = Response(document.original_pdf, mimetype="application/pdf")
        response.headers["Content-Disposition"] = content_disposition(document.filename)
        return response

    @app.errorhandler(413)
    def request_too_large(exc):
        return page(error="That request is too large.", status=413)

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
    parser.add_argument("--dogfood-log", type=Path, metavar="PATH",
                        help="Append body-free local turn diagnostics to a chosen JSONL file.")
    parser.add_argument("--forensic-log", type=Path, metavar="PATH",
                        help="Append source-bearing observer events to a sensitive local JSONL file.")
    parser.add_argument("--port", type=int, default=_PORT, help=f"Local HTTP port (default: {_PORT}).")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    try:
        serve(create_app(database=args.database, dogfood_log=args.dogfood_log,
                         forensic_log=args.forensic_log), port=args.port)
    except KeyboardInterrupt:
        pass
    except (OSError, SessionStoreError):
        print("The Reading Room could not start. Check the database or log locations, or choose another --port.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
