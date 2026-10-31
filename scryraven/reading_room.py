"""Local HTTP shell over ResearchSession and SessionStore; no research decisions."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import uuid4

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for
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
    prepare_pdf,
    textless_page_warning,
)
from scryraven.dogfood_diagnostics import DogfoodLog, TurnDiagnostics
from scryraven.forensic_log import ForensicLog
from scryraven.images import (
    IMAGE_ERROR_MESSAGES,
    IMAGE_ID,
    MAX_ATTACHMENT_REQUEST_BYTES,
    MAX_ATTACHMENTS_PER_QUESTION,
    MAX_IMAGE_BYTES,
    ImageRejected,
    image_preview,
    prepare_image,
)
from scryraven.presentation import (
    answer_html,
    citation_preview_html,
    source_body_html,
    source_free_supported,
    source_label,
)
from scryraven.research_jobs import ResearchJobManager
from scryraven.session_store import (
    SessionConflictError,
    SessionStore,
    SessionStoreError,
    SQLiteSessionStore,
)

_HOST = "127.0.0.1"
_PORT = 7331
_FORM_BODY_BYTES = 256 * 1024
_QUESTION_UPLOADS = {"ask"}
_LANGUAGES = {"en", "match", "es", "fr", "de", "pl", "pt", "ja", "zh", "ar"}


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

    def claim(self, token, action, session_id="", *, replayable=False):
        try:
            saved_action, saved_id, revision, _ = self.signer.loads(token, max_age=self.lifetime)
        except (BadSignature, ValueError, TypeError):
            raise _FormError() from None
        if (saved_action, saved_id) != (action, session_id) or type(revision) is not int or revision < 0:
            raise _FormError()
        if replayable:
            return revision
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
    # Multipart questions have bounded file bodies; text fields stay small.
    app.config.update(MAX_CONTENT_LENGTH=MAX_ATTACHMENT_REQUEST_BYTES + _FORM_BODY_BYTES,
                      MAX_FORM_MEMORY_SIZE=_FORM_BODY_BYTES, MAX_FORM_PARTS=32,
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
    diagnostic_runs = {}

    def job_options(job):
        turn_diagnostics = TurnDiagnostics(started_at=monotonic(), clock=monotonic) if diagnostics else None
        diagnostic_runs[job.job_id] = turn_diagnostics
        turn_options = dict(options)
        prior_observer = turn_options.get("observe")

        def observe(event):
            if turn_diagnostics is not None:
                try:
                    turn_diagnostics.observe(event)
                except Exception:
                    pass
            if forensics is not None:
                try:
                    forensics.append(event, session_id=job.session_id, revision_before=job.revision)
                except Exception:
                    forensics.disable()
            if prior_observer is not None:
                try:
                    prior_observer(event)
                except Exception:
                    pass

        turn_options["observe"] = observe
        return turn_options

    def job_finished(job, result, error, session):
        turn_diagnostics = diagnostic_runs.pop(job.job_id, None)
        if turn_diagnostics is not None:
            try:
                diagnostics.append(turn_diagnostics.record(
                    session_id=job.session_id, revision_before=job.revision,
                    revision_after=session.metadata.revision if error is None and session else None,
                    result=result, error=error,
                ))
            except Exception:
                print("Reading Room dogfood diagnostics stopped: the local log could not be written.",
                      file=sys.stderr, flush=True)

    try:
        jobs = ResearchJobManager(custody, session_options_factory=job_options, on_finished=job_finished)
    except SessionStoreError as exc:
        if exc.code == "research_server_owned":
            raise OSError("reading_room_already_running") from None
        jobs = None
    app.extensions["research_jobs"] = jobs

    @app.before_request
    def protect_local_requests():
        # Host validation also prevents DNS rebinding. Do not trust proxy headers.
        question_upload = request.endpoint in _QUESTION_UPLOADS
        limit = (MAX_ATTACHMENT_REQUEST_BYTES + _FORM_BODY_BYTES if question_upload
                 else _FORM_BODY_BYTES)
        # This also bounds a body without Content-Length.
        request.max_content_length = limit
        request.max_form_memory_size = _FORM_BODY_BYTES if question_upload else limit
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            if (origin is not None and origin != request.host_url.rstrip("/")) or (
                request.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                abort(403)
            allowed_types = ({"multipart/form-data", "application/x-www-form-urlencoded"} if question_upload
                             else {"application/x-www-form-urlencoded"})
            if request.mimetype not in allowed_types:
                abort(415)
            if request.content_length is not None and request.content_length > limit:
                abort(413)

    @app.after_request
    def response_safety(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; "
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

    def public_job(job):
        if job is None:
            return None
        messages = {
            "queued": "Queued. Research will start when a local worker is available.",
            "researching": "Researching. You can browse other conversations while this continues.",
            "completed": "Research completed.",
            "failed": "Research did not complete. Your question and attachments are saved. You can retry explicitly.",
            "interrupted": "Research was interrupted when the local server stopped. Retry explicitly to start again.",
        }
        error = IMAGE_ERROR_MESSAGES.get(job.error_code, messages[job.state])
        if job.error_code == "storage_interrupted":
            error = ("Research was interrupted because local storage became unavailable. "
                     "Your question and attachments are saved; retry explicitly.")
        return {"job_id": job.job_id, "session_id": job.session_id, "state": job.state,
                "question": job.question, "revision": job.revision,
                "error": error, "error_code": job.error_code}

    def attachment_links(saved, document_ids=(), image_ids=()):
        result = []
        for document in saved.documents:
            if document.document_id in document_ids:
                result.append({"id": document.document_id, "filename": document.filename,
                               "media_type": "application/pdf",
                               "href": url_for("original_pdf", session_id=saved.metadata.session_id,
                                               document_id=document.document_id)})
        for item in saved.images:
            if item.image_id in image_ids:
                result.append({"id": item.image_id, "filename": item.filename,
                               "media_type": item.media_type,
                               "href": url_for("original_image", session_id=saved.metadata.session_id,
                                               image_id=item.image_id),
                               "preview_href": url_for("preview_image", session_id=saved.metadata.session_id,
                                                       image_id=item.image_id)})
        return result

    def page(session_id=None, *, question="", error=None, status=200, confirmation=False, edit_title=False):
        try:
            history = custody.list_sessions()
            saved = custody.load(session_id) if session_id else None
            if jobs is None:
                raise SessionStoreError()
            history_jobs = {}
            for research_job in jobs.list():
                history_jobs.setdefault(research_job.session_id, public_job(research_job))
            job = history_jobs.get(session_id)
            session_jobs = {item.revision + 1: item for item in jobs.list(session_id=session_id)
                            if item.state == "completed"} if saved else {}
            if job and saved:
                pending = next(item for item in jobs.list(session_id=session_id) if item.job_id == job["job_id"])
                job["attachments"] = attachment_links(saved, pending.document_ids, pending.image_ids)
        except SessionStoreError as exc:
            if exc.code == "session_not_found":
                if question or error:
                    return page(question=question, error=error or "That conversation was deleted. Your question is kept below.", status=status)
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
                "answer": Markup(answer_html(turn, source_prefix=prefix, citation_previews=True)),
                "attachments": attachment_links(saved,
                    session_jobs[number].document_ids if number in session_jobs else (), turn.image_ids),
                "sources": [{"number": c.number, "id": prefix + str(c.number), "title": source_label(c),
                             "preview": Markup(citation_preview_html(
                                 c, original_href=(url_for("original_pdf", session_id=metadata.session_id,
                                                          document_id=c.document_id)
                                                   if c.source_kind == "user_document" and c.document_id else None),
                             )),
                             "body": Markup(source_body_html(
                                 c, collapse_long=True, uses=turn.citation_uses,
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
            images=attachment_links(saved, image_ids=tuple(item.image_id for item in saved.images)) if saved else [],
            job=job, history_jobs=history_jobs, idempotency_key=uuid4().hex,
            citation_language=metadata.citation_language if metadata else "en",
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

    def read_attachments():
        uploads = request.files.getlist("files")
        # Unknown file fields must never be silently discarded.
        if any(key != "files" for key in request.files):
            raise ImageRejected("image_type_rejected")
        if len(uploads) > MAX_ATTACHMENTS_PER_QUESTION:
            raise ImageRejected("attachment_count_exceeded")
        documents, images, total = [], [], 0
        for storage in uploads:
            try:
                data = storage.read(MAX_PDF_BYTES + 1)
            finally:
                storage.close()
            if not storage.filename and not data:
                continue  # An untouched native file picker sends an empty part.
            if not storage.filename:
                raise ImageRejected("image_type_rejected")
            total += len(data)
            if total > MAX_ATTACHMENT_REQUEST_BYTES:
                raise ImageRejected("attachment_request_too_large")
            filename, media_type = storage.filename or "", storage.mimetype or ""
            if data.startswith(b"%PDF-") or media_type == "application/pdf" or filename.lower().endswith(".pdf"):
                documents.append(prepare_pdf(filename, media_type, data))
            else:
                if len(data) > MAX_IMAGE_BYTES:
                    raise ImageRejected("image_too_large")
                images.append(prepare_image(filename, media_type, data))
        return tuple(documents), tuple(images)

    @app.post("/ask")
    @app.post("/sessions/<session_id>/ask")
    def ask(session_id=None):
        question = request.form.get("question", "").strip()
        try:
            revision = forms.claim(request.form.get("form_token", ""), "ask", session_id or "", replayable=True)
        except _FormError:
            return page(session_id, question=question, status=409,
                        error="This form has expired. Review your question and submit it again.")
        if not question:
            return page(session_id, error="Write a research question to begin.", status=400)
        if len(question) > 20000:
            return page(session_id, question=question, error="Keep the question within 20,000 characters.", status=400)
        language = request.form.get("citation_language", "en")
        if language not in _LANGUAGES:
            return page(session_id, question=question, error="Choose a citation explanation language.", status=400)
        key = request.form.get("idempotency_key", "") or request.form.get("form_token", "")
        try:
            documents, images = read_attachments()
            job = jobs.submit(question, session_id=session_id, revision=revision,
                              idempotency_key=key, documents=documents, images=images,
                              retained_image_ids=tuple(request.form.getlist("retained_image_ids")),
                              citation_language=language)
        except (DocumentRejected, ImageRejected) as exc:
            message = DOCUMENT_ERROR_MESSAGES.get(exc.code) or IMAGE_ERROR_MESSAGES.get(exc.code)
            return page(session_id, question=question, error=message, status=400)
        except SessionStoreError as exc:
            if exc.code in {"attachment_count_exceeded", "attachment_request_too_large", "invalid_image_selection"}:
                return page(session_id, question=question, status=400,
                            error=IMAGE_ERROR_MESSAGES.get(exc.code, "Choose an image attached to this conversation."))
            messages = {
                "session_not_found": "That conversation was deleted. Your question is kept below.",
                "session_conflict": "This conversation changed. Review the latest answer before submitting again.",
                "session_busy": "This conversation already has an active question. Your unsent question is kept below.",
                "research_queue_full": "The local research queue is full. Your question is kept below; try again shortly.",
                "submission_conflict": "An earlier version of this question is already saved. This edited draft was not sent.",
            }
            response = app.make_response(page(session_id, question=question, status=409,
                error=messages.get(exc.code, "The question could not be accepted. It is kept below; try again.")))
            if exc.code == "submission_conflict":
                accepted = custody.find_submission(key)
                if accepted:
                    response.headers["X-ScryRaven-Submission-Conflict"] = "1"
                    response.headers["X-ScryRaven-Submission-Location"] = url_for("open_session", session_id=accepted.session_id)
            return response
        return redirect(url_for("open_session", session_id=job.session_id, _anchor="research-status"), 303)

    @app.get("/jobs/status")
    def job_status():
        latest = {}
        for item in jobs.list():
            latest.setdefault(item.session_id, public_job(item))
        return jsonify(jobs=list(latest.values()))

    @app.post("/sessions/<session_id>/jobs/<job_id>/retry")
    def retry_job(session_id, job_id):
        revision = claim("retry", session_id)
        previous = jobs.get(job_id)
        if previous.session_id != session_id or previous.state not in {"failed", "interrupted"}:
            return page(session_id, error="That research run cannot be retried.", status=409)
        saved = custody.load(session_id)
        if saved.metadata.revision != revision or revision != previous.revision:
            return page(session_id, question=previous.question,
                        error="The conversation changed. Review it before submitting a new question.", status=409)
        job = jobs.retry(job_id, idempotency_key=request.form.get("form_token", ""))
        return redirect(url_for("open_session", session_id=job.session_id, _anchor="research-status"), 303)

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
        try:
            custody.delete(session_id, revision=revision)
        except SessionStoreError as exc:
            if exc.code == "session_busy":
                return page(session_id, error="Research is active in this conversation. Wait for it to finish before deleting.",
                            status=409)
            raise
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

    def owned_image(session_id, image_id):
        if not IMAGE_ID.fullmatch(image_id or ""):
            abort(404)
        try:
            saved = custody.load(session_id)
        except SessionStoreError as exc:
            if exc.code == "session_not_found":
                abort(404)
            raise
        item = next((item for item in saved.images if item.image_id == image_id), None)
        if item is None:
            abort(404)
        return item

    @app.get("/sessions/<session_id>/images/<image_id>/preview")
    def preview_image(session_id, image_id):
        return Response(image_preview(owned_image(session_id, image_id)), mimetype="image/png")

    @app.get("/sessions/<session_id>/images/<image_id>/original")
    def original_image(session_id, image_id):
        image = owned_image(session_id, image_id)
        response = Response(image.original_image, mimetype=image.media_type)
        response.headers["Content-Disposition"] = content_disposition(image.filename).replace("inline;", "attachment;", 1)
        return response

    @app.errorhandler(413)
    def request_too_large(exc):
        return page(error="That request is too large.", status=413)

    return app


class _QuietHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        # Local paths, questions and request payloads are not an access log.
        pass


def serve(app: Flask, *, port: int = _PORT, on_ready=None) -> None:
    """Local HTTP navigation and bounded server-owned research workers."""
    server = None
    try:
        server = make_server(_HOST, port, app, threaded=True, request_handler=_QuietHandler)
        if on_ready is not None:
            on_ready(server.server_port)
        print(f"ScryRaven Reading Room: http://{_HOST}:{server.server_port}", flush=True)
        print("Open this address in your browser. Press Ctrl+C to stop.", flush=True)
        server.serve_forever()
    finally:
        try:
            jobs = getattr(app, "extensions", {}).get("research_jobs")
            if jobs is not None:
                jobs.shutdown()
        finally:
            if server is not None:
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
