"""Local HTTP shell over ResearchSession and SessionStore; no research decisions."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from base64 import b64encode
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from tempfile import SpooledTemporaryFile
from threading import Lock
from time import monotonic
from uuid import uuid4
from zipfile import ZipFile

from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, send_file, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer
from markupsafe import Markup
from werkzeug.exceptions import HTTPException, SecurityError
from werkzeug.serving import WSGIRequestHandler, make_server

from scryraven import dictation
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
from scryraven.model import ModelError, OpenAIModel
from scryraven.presentation import (
    answer_html,
    citation_preview_html,
    source_body_html,
    source_free_supported,
    source_label,
)
from scryraven.research_jobs import ResearchJobManager
from scryraven.run_settings import BILLED_BACKENDS, RunSettings, settings_from_form
from scryraven.run_settings import ERROR_MESSAGES as RUN_SETTINGS_ERRORS
from scryraven.session_store import (
    CITATION_LANGUAGES,
    MAX_ANSWER_FEEDBACK_CHARS,
    SessionConflictError,
    SessionStore,
    SessionStoreError,
    SQLiteSessionStore,
    _encode,
)

_HOST = "127.0.0.1"
_PORT = 7331
_FORM_BODY_BYTES = 256 * 1024
_QUESTION_UPLOADS = {"ask"}

# WebKit can retry an initial fragment scroll while deferred assets are pending.
# Install this before the readable HTML so deliberate reading takes precedence.
_READING_CONTEXT_SCRIPT = """(() => {
  function preserveReadingContext(event) {
    if (document.readyState === 'complete' || !/^#(?:turn-\\d+|research-status)$/.test(location.hash)) return;
    if (event.target.closest?.('.reading-scroll')) {
      history.replaceState(history.state, '', location.pathname + location.search);
    }
  }
  document.addEventListener('pointerdown', preserveReadingContext, true);
  document.addEventListener('keydown', preserveReadingContext, true);
})();"""
_READING_CONTEXT_SCRIPT_HASH = b64encode(sha256(_READING_CONTEXT_SCRIPT.encode()).digest()).decode()


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

    def issue(self, action, session_id="", revision=0, *, principal=""):
        return self.signer.dumps([action, session_id, revision, secrets.token_urlsafe(20), principal])

    def claim(self, token, action, session_id="", *, replayable=False, principal=""):
        try:
            saved_action, saved_id, revision, _, saved_principal = self.signer.loads(token, max_age=self.lifetime)
        except (BadSignature, ValueError, TypeError):
            raise _FormError() from None
        if ((saved_action, saved_id, saved_principal) != (action, session_id, principal)
                or type(revision) is not int or revision < 0):
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
               run_model_factory: Callable | None = None,
               dogfood_log: str | Path | None = None,
               forensic_log: str | Path | None = None,
               hosted=None, identity_validator=None) -> Flask:
    """Inject only the existing store and ResearchSession's ordinary I/O options."""
    app = Flask(__name__)
    app.jinja_env.globals["reading_context_script"] = Markup(_READING_CONTEXT_SCRIPT)
    # Multipart questions have bounded file bodies; text fields stay small.
    app.config.update(MAX_CONTENT_LENGTH=MAX_ATTACHMENT_REQUEST_BYTES + _FORM_BODY_BYTES,
                      MAX_FORM_MEMORY_SIZE=_FORM_BODY_BYTES, MAX_FORM_PARTS=32,
                      TRUSTED_HOSTS=["127.0.0.1", "localhost"])
    chosen_database = database if database is not None else hosted.database if hosted is not None else None
    custody = store if store is not None else SQLiteSessionStore(chosen_database)
    validator = hosted_diagnostics = None
    hosted_preferences = None
    if hosted is not None:
        from scryraven.hosted import AccessTokenValidator
        from scryraven.hosted_diagnostics import HostedDiagnostics
        from scryraven.hosted_preferences import HostedPreferences

        if not isinstance(custody, SQLiteSessionStore):
            raise ValueError("hosted_sqlite_required")
        if custody.path != hosted.database.resolve():
            raise ValueError("hosted_database_location_required")
        if any(item.owner_id is None for item in custody.list_sessions()):
            raise ValueError("hosted_database_contains_unowned_sessions")
        if dogfood_log is not None or forensic_log is not None:
            raise ValueError("hosted_diagnostics_location_required")
        app.config["TRUSTED_HOSTS"] = [hosted.hostname, "healthcheck.railway.app"]
        validator = identity_validator or AccessTokenValidator(hosted)
        hosted_diagnostics = HostedDiagnostics(hosted.diagnostics_dir,
            retention_days=hosted.forensic_days, max_bytes=hosted.forensic_max_bytes)
        app.extensions["hosted_diagnostics"] = hosted_diagnostics
        hosted_preferences = HostedPreferences(custody, hosted.run_settings)
    options = dict(session_options or {})
    initial_model = options.get("model")
    if initial_model is None:
        initial_model = (OpenAIModel(hosted.run_settings.model_config(), backend="api")
                         if hosted is not None else OpenAIModel())
    initial_settings = hosted.run_settings if hosted is not None else RunSettings.effective(initial_model, options.get("limits"))
    initial_config = getattr(initial_model, "config", None)
    mixed_processing = (initial_settings.backend == "openai" and initial_config is not None
                        and initial_config.research.service_tier != initial_config.answer.service_tier)
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
    transcription_slots = dictation.TranscriptionSlots()
    diagnostic_runs = {}
    usage_runs = {}
    job_owners = {}

    def require_billing_authorization(backend):
        if hosted is not None:
            if backend != "openai":
                raise ModelError("invalid_run_settings")
            return
        if backend in BILLED_BACKENDS and not custody.get_billing_authorizations()[backend]:
            raise ModelError("paid_inference_authorization_required")

    def job_options(job):
        owner_id = custody.get_metadata(job.session_id).owner_id if hosted is not None else None
        if hosted is not None:
            job_owners[job.job_id] = owner_id
        turn_diagnostics = TurnDiagnostics(started_at=monotonic(), clock=monotonic) if diagnostics or hosted_diagnostics else None
        diagnostic_runs[job.job_id] = turn_diagnostics
        turn_options = dict(options)
        settings = job.run_settings
        if settings is None:
            raise ValueError("historical_run_settings_unknown")
        if hosted is not None:
            from scryraven.hosted_preferences import validate_hosted_settings
            validate_hosted_settings(settings)
        require_billing_authorization(settings.backend)
        records = []
        usage_runs[job.job_id] = records
        base_model = initial_model
        if run_model_factory is not None:
            turn_model = run_model_factory(settings)
            if isinstance(turn_model, OpenAIModel):
                turn_model = turn_model.with_config(
                    settings.model_config(), backend="api" if settings.backend == "openai" else settings.backend)
        elif isinstance(base_model, OpenAIModel):
            turn_model = base_model.with_config(
                settings.model_config(), backend="api" if settings.backend == "openai" else settings.backend)
        elif base_model is not None:
            # Existing controlled transport injection is retained for offline
            # application checks. Production launches inject OpenAIModel.
            turn_model = base_model
        else:
            turn_model = OpenAIModel(settings.model_config(),
                                     backend="api" if settings.backend == "openai" else settings.backend)
        if isinstance(turn_model, OpenAIModel):
            prior_usage = turn_model.usage_observer
            prior_authorizer = turn_model.request_authorizer

            def authorize_request():
                require_billing_authorization(settings.backend)
                if prior_authorizer is not None:
                    prior_authorizer()

            turn_model.request_authorizer = authorize_request

            def usage(item):
                records.append({
                    "role": item.stage, "model": item.model,
                    "reasoning": settings.answer_reasoning if item.stage == "answer" else settings.research_reasoning,
                    "backend": settings.backend,
                    "returned_model": getattr(item, "returned_model", None),
                    "provider": getattr(item, "provider", None),
                    "reported_cost_usd": getattr(item, "reported_cost_usd", None),
                    "requested_service_tier": item.requested_service_tier,
                    "returned_service_tier": item.returned_service_tier,
                    "input_tokens": item.input_tokens, "output_tokens": item.output_tokens,
                    "cached_input_tokens": item.cached_input_tokens,
                    "cache_write_tokens": item.cache_write_tokens,
                    "reasoning_tokens": item.reasoning_tokens,
                })
                if prior_usage:
                    prior_usage(item)

            turn_model.usage_observer = usage
            turn_model.validate_configuration()
        turn_options["model"] = turn_model
        turn_options["limits"] = settings.limits()
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
            if hosted_diagnostics is not None:
                hosted_diagnostics.observe(event, job=job, owner_id=owner_id)
            if prior_observer is not None:
                try:
                    prior_observer(event)
                except Exception:
                    pass

        turn_options["observe"] = observe
        return turn_options

    def job_finished(job, result, error, session):
        records = usage_runs.pop(job.job_id, [])
        try:
            if job.state != "completed":
                custody.save_run_receipt(job.job_id, {
                    "requests": records, "estimated_cost_usd": None, "actual_billed_usd": None,
                })
        except (SessionStoreError, ValueError):
            pass  # Usage remains unknown if optional receipt storage is unavailable.
        turn_diagnostics = diagnostic_runs.pop(job.job_id, None)
        record = None
        if turn_diagnostics is not None:
            try:
                record = turn_diagnostics.record(
                    session_id=job.session_id, revision_before=job.revision,
                    revision_after=session.metadata.revision if error is None and session else None,
                    result=result, error=error,
                )
                if diagnostics is not None:
                    diagnostics.append(record)
            except Exception:
                print("Reading Room dogfood diagnostics stopped: the local log could not be written.",
                      file=sys.stderr, flush=True)
        if hosted_diagnostics is not None:
            hosted_diagnostics.finish(record, job=job, owner_id=job_owners.pop(job.job_id, None))

    try:
        jobs = ResearchJobManager(custody, concurrency=4 if hosted is not None else 2,
                                  session_options_factory=job_options, on_finished=job_finished,
                                  completion_receipt_factory=lambda job: {
                                      "requests": list(usage_runs.get(job.job_id, [])),
                                      "estimated_cost_usd": None, "actual_billed_usd": None,
                                  })
    except SessionStoreError as exc:
        if exc.code == "research_server_owned":
            raise OSError("reading_room_already_running") from None
        jobs = None
    app.extensions["research_jobs"] = jobs

    def principal():
        return g.identity.email if hosted is not None else ""

    def visible_sessions():
        if hosted is None:
            return custody.list_sessions()
        return custody.list_sessions(owner_id=principal())

    def admission_identity():
        return ({"owner_id": principal(), "submission_quota": hosted.submissions_per_day}
                if hosted is not None else {})

    def current_hosted_settings():
        return hosted_preferences.for_user(principal(), admin=g.identity.is_admin)

    @app.context_processor
    def hosted_context():
        identity = getattr(g, "identity", None)
        from scryraven.hosted_preferences import HOSTED_MODEL_CHOICES
        return {"hosted_mode": hosted is not None, "identity": identity,
                "browser_identity": sha256(identity.email.encode()).hexdigest() if identity else "local",
                "hosted_model_choices": HOSTED_MODEL_CHOICES if hosted is not None else {},
                "hosted_preferences": hosted_preferences.defaults().to_dict() if hosted is not None else {}}

    @app.before_request
    def protect_local_requests():
        if hosted is not None:
            from scryraven.hosted import AccessDenied

            if request.endpoint == "health":
                hosted_diagnostics.maintenance()
                return None
            if request.host.split(":", 1)[0] != hosted.hostname:
                abort(400)
            try:
                g.identity = validator.validate(request.headers.get("Cf-Access-Jwt-Assertion", ""))
            except AccessDenied:
                abort(401)
            if request.endpoint in {"admin_sessions", "export_session"} and not g.identity.is_admin:
                abort(404)
            if request.endpoint == "update_billing_authorization":
                abort(403)
            if request.endpoint == "update_hosted_preferences" and not g.identity.is_admin:
                abort(403)
            session_id = (request.view_args or {}).get("session_id")
            if session_id:
                try:
                    metadata = custody.get_metadata(session_id)
                except SessionStoreError as exc:
                    if exc.code == "session_not_found":
                        abort(404)
                    raise
                if metadata.owner_id is None or (metadata.owner_id != principal() and not g.identity.is_admin):
                    abort(404)
                g.read_only = metadata.owner_id != principal()
                if g.read_only and (request.method not in {"GET", "HEAD", "OPTIONS"}
                                    or request.endpoint == "confirm_delete"):
                    abort(404)
            if hosted_diagnostics is not None:
                hosted_diagnostics.maintenance()
        # Host validation also prevents DNS rebinding. Do not trust proxy headers.
        question_upload = request.endpoint in _QUESTION_UPLOADS
        dictation_upload = request.endpoint == "transcribe_question"
        multipart_upload = question_upload and request.mimetype == "multipart/form-data"
        limit = (MAX_ATTACHMENT_REQUEST_BYTES + _FORM_BODY_BYTES if multipart_upload
                 else _FORM_BODY_BYTES)
        if dictation_upload:
            limit = dictation.MAX_AUDIO_BYTES
        # Only actual file uploads need the larger body allowance. URL-encoded
        # bodies are bounded here, including streams without Content-Length,
        # independently of the parser's multipart form-memory limit.
        request.max_content_length = limit
        if dictation_upload:
            # Keep one byte to distinguish oversized streams from an exact-limit WAV.
            request.max_content_length = limit + 1
        request.max_form_memory_size = _FORM_BODY_BYTES if question_upload else limit
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("Origin")
            expected_origin = hosted.origin if hosted is not None else request.host_url.rstrip("/")
            if (origin is not None and origin != expected_origin) or (
                request.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                abort(403)
            allowed_types = {"application/x-www-form-urlencoded"}
            if question_upload:
                allowed_types.add("multipart/form-data")
            if dictation_upload:
                allowed_types = {"audio/wav"}
            if request.mimetype not in allowed_types:
                abort(415)
            if request.content_length is not None and request.content_length > limit:
                abort(413)
            if request.mimetype == "application/x-www-form-urlencoded" and request.content_length is None:
                # LimitedStream.read() can stop at its ceiling without signaling
                # overflow. Probe one extra byte, then parse only cached bytes.
                request.max_content_length = limit + 1
                try:
                    body = request.get_data(cache=True)
                finally:
                    request.max_content_length = limit
                if len(body) > limit:
                    abort(413)

    @app.after_request
    def response_safety(response):
        response.headers["Content-Security-Policy"] = (
            f"default-src 'none'; script-src 'self' 'sha256-{_READING_CONTEXT_SCRIPT_HASH}'; "
            "style-src 'self'; img-src 'self' blob:; connect-src 'self'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"
        )
        # Browsers can send Origin: null on native POSTs under no-referrer.
        # Same-origin preserves our local Origin check; external links still
        # carry rel=noreferrer and disclose no local referrer.
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if hosted is not None:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def public_job(job):
        if job is None:
            return None
        messages = {
            "queued": "Your question is queued. It will begin automatically when a worker is available. You may navigate away.",
            "researching": "Researching. You can browse other conversations while this continues.",
            "completed": "Research completed.",
            "failed": "Research did not complete. Your question and attachments are saved. You can retry explicitly.",
            "interrupted": "Research was interrupted. Your question and attachments are saved. Retry explicitly to start again.",
        }
        error = IMAGE_ERROR_MESSAGES.get(job.error_code, messages[job.state])
        error = RUN_SETTINGS_ERRORS.get(job.error_code, error)
        if job.error_code == "storage_interrupted":
            error = ("Research was interrupted because application storage became unavailable. "
                     "Your question and attachments are saved; retry explicitly.")
        elif job.state == "interrupted" and job.error_code == "server_interrupted":
            error = ("The server interrupted this run. Your question and attachments are saved; "
                     "retry explicitly to start again.")
        return {"job_id": job.job_id, "session_id": job.session_id, "state": job.state,
                "question": job.question, "revision": job.revision,
                "error": error, "error_code": job.error_code,
                "run_settings": job.run_settings.to_dict() if job.run_settings else None,
                "run_receipt": job.run_receipt}

    def job_summaries(records, visible_ids, owned_ids):
        latest = {}
        for item in records:
            if item.session_id not in visible_ids:
                continue
            if item.session_id not in latest:
                latest[item.session_id] = dict(public_job(item), new_answer=None)
            summary = latest[item.session_id]
            if (item.session_id in owned_ids and summary["new_answer"] is None
                    and item.state == "completed" and not item.viewed):
                summary["new_answer"] = {"job_id": item.job_id, "turn": item.revision + 1}
        return latest

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

    def page(session_id=None, *, question="", error=None, status=200, confirmation=False, edit_title=False,
             feedback_turn=None, feedback_error=None, feedback_text=""):
        try:
            history = visible_sessions()
            if jobs is None:
                raise SessionStoreError()
            # Completion commits its answer and job state atomically. Read jobs
            # first so a completed job never points beyond this page's turns.
            records = jobs.list()
            saved = custody.load(session_id) if session_id else None
            feedback = custody.list_feedback(session_id) if saved and hosted is not None else ()
            visible_ids = {item.session_id for item in history}
            owned_ids = {item.session_id for item in history if item.owner_id == (principal() or None)}
            history_jobs = job_summaries(records, visible_ids | {session_id}, owned_ids)
            job = history_jobs.get(session_id)
            session_records = tuple(item for item in records if item.session_id == session_id) if saved else ()
            session_jobs = {item.revision + 1: item for item in session_records if item.state == "completed"}
            if job and saved:
                pending = session_records[0]
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
        document_hrefs = {}
        if saved:
            for document in saved.documents:
                href = url_for("original_pdf", session_id=metadata.session_id, document_id=document.document_id)
                document_hrefs[document.document_id] = href
                documents.append({
                    "filename": document.filename, "pages": document.page_count,
                    "textless": textless_page_warning(document.textless_page_count),
                    "href": href,
                })
        turns = []
        for number, turn in enumerate(saved.state.turns if saved else (), 1):
            prefix = f"turn-{number}-source-"
            completed = session_jobs.get(number)
            turns.append({
                "number": number, "turn_index": number, "question": turn.question, "posture": turn.posture,
                "unviewed_job_id": (completed.job_id if completed and not completed.viewed
                                    and session_id in owned_ids else None),
                "feedback": tuple(item for item in feedback if item.turn_index == number),
                "feedback_error": feedback_error if feedback_turn == number else None,
                "feedback_text": feedback_text if feedback_turn == number else "",
                "feedback_notice": ({"feedback_sent": "Feedback sent.", "feedback_removed": "Feedback removed."}
                                    .get(request.args.get("notice"))
                                    if request.args.get("feedback_turn") == str(number) else None),
                "operating_bound": turn.stop_reason == "research_bound",
                "source_free": source_free_supported(turn),
                "answer": Markup(answer_html(turn, source_prefix=prefix, citation_previews=True,
                                             document_hrefs=document_hrefs)),
                "run_settings": (session_jobs[number].run_settings.to_dict()
                                 if number in session_jobs and session_jobs[number].run_settings else None),
                "run_receipt": session_jobs[number].run_receipt if number in session_jobs else None,
                "attachments": attachment_links(saved,
                    session_jobs[number].document_ids if number in session_jobs else (), turn.image_ids),
                "sources": [{"number": c.number, "id": prefix + str(c.number), "title": source_label(c),
                             "preview": Markup(citation_preview_html(
                                 c, original_href=document_hrefs.get(c.document_id),
                             )),
                             "body": Markup(source_body_html(
                                 c, collapse_long=True, uses=turn.citation_uses,
                                 original_href=document_hrefs.get(c.document_id),
                             ))} for c in turn.citations],
            })
        global_actions = {"billing", "hosted-settings", "processing"}
        def issue(action):
            # These actions belong to an immutable completed answer, independently
            # of the research-session revision displayed by this page.
            revision_bound = (action not in global_actions and action != "source-language"
                              and not action.startswith(("feedback:", "feedback-delete:", "view-answer:")))
            return forms.issue(action, metadata.session_id if metadata and action not in global_actions else "",
                               metadata.revision if metadata and revision_bound else 0, principal=principal())
        notice = {"missing": "That session is no longer available. Your other research is here.",
                  "deleted": "Session deleted.", "renamed": "Session renamed.",
                  "already_attached": ALREADY_ATTACHED_NOTICE,
                  "settings_saved": "Settings saved. Accepted questions keep their original settings."}.get(request.args.get("notice"))
        billing_authorizations = {} if hosted is not None else custody.get_billing_authorizations()
        dictation_configured = dictation.available()
        dictation_authorized = hosted is not None or billing_authorizations["openai"]
        dictation_error = ""
        if not dictation_configured:
            dictation_error = dictation.API_UNAVAILABLE
        elif not dictation_authorized:
            dictation_error = dictation.BILLING_REQUIRED
        return render_template(
            "reading_room.html", history=history, saved=saved, turns=turns, documents=documents,
            images=attachment_links(saved, image_ids=tuple(item.image_id for item in saved.images)) if saved else [],
            job=job, history_jobs=history_jobs, idempotency_key=uuid4().hex,
            citation_language=metadata.citation_language if metadata else getattr(g, "new_citation_language", "en"),
            run_settings=(current_hosted_settings() if hosted is not None else custody.get_run_settings() or initial_settings).to_dict(),
            billing_authorizations=billing_authorizations,
            dictation_configured=dictation_configured, dictation_enabled=not dictation_error,
            dictation_error=dictation_error,
            dictation_token=forms.issue("dictation", session_id or "", principal=principal()),
            dictation_max_seconds=dictation.MAX_SECONDS,
            run_settings_profiles=({} if hosted is not None else {backend: settings.to_dict()
                                   for backend, settings in custody.get_run_settings_profiles().items()}),
            initial_processing_profile=({
                "research": initial_config.research.service_tier or "model default",
                "answer": initial_config.answer.service_tier or "model default",
            } if mixed_processing and custody.get_run_settings() is None else None),
            text_only_warning=TEXT_ONLY_WARNING, question=question,
            error=error, notice=notice, confirmation=confirmation, form_token=issue,
            renaming=bool(saved and (edit_title or request.args.get("edit") == "rename")),
            read_only=getattr(g, "read_only", False),
            submissions_per_day=hosted.submissions_per_day if hosted is not None else None,
            max_feedback_chars=MAX_ANSWER_FEEDBACK_CHARS,
        ), status

    @app.get("/")
    def new_research():
        return page()

    @app.get("/healthz")
    def health():
        # No user data, storage paths, provider checks or authenticated state.
        if hosted is None:
            abort(404)
        return jsonify(status="ok")

    @app.get("/admin")
    def admin_sessions():
        if hosted is None:
            abort(404)
        sessions = tuple(item for item in custody.list_sessions() if item.owner_id is not None)
        return render_template("admin_sessions.html", sessions=sessions,
                               usage=hosted_diagnostics.usage(), database_bytes=custody.path.stat().st_size)

    @app.get("/admin/sessions/<session_id>/export")
    def export_session(session_id):
        if hosted is None:
            abort(404)
        saved = custody.load(session_id)
        output = SpooledTemporaryFile(max_size=2 * 1024 * 1024, mode="w+b", dir=hosted.data_dir)
        try:
            with ZipFile(output, "w") as archive:
                documents = []
                for document in saved.documents:
                    item = asdict(document)
                    content = item.pop("original_pdf")
                    item["original_path"] = f"attachments/{document.document_id}.pdf"
                    archive.writestr(item["original_path"], content)
                    documents.append(item)
                images = []
                for image in saved.images:
                    item = asdict(image)
                    content = item.pop("original_image")
                    item["original_path"] = f"attachments/{image.image_id}"
                    archive.writestr(item["original_path"], content)
                    images.append(item)
                record = {"format": "scryraven-session-export-1", "metadata": asdict(saved.metadata),
                          "state": json.loads(_encode(saved.state, saved.documents, saved.images)),
                          "documents": documents, "images": images,
                          "jobs": [{key: value for key, value in asdict(item).items() if key != "viewed"}
                                   for item in jobs.list(session_id)],
                          "answer_feedback": [dict(asdict(item), provenance="authenticated_participant")
                                              for item in custody.list_feedback(session_id)
                                              if item.turn_index <= len(saved.state.turns)],
                          "answer_feedback_provenance": {
                              "author_id": "Server-verified Cloudflare Access participant email at submission.",
                              "turn_index": "Immutable 1-based completed answer index within session_id.",
                              "created_at": "Server UTC timestamp at submission.",
                              "text": "Participant feedback to the administrator; never research context or Evidence.",
                          },
                          "diagnostics": "Available records only; retention or write limits may have removed records."}
                archive.writestr("session.json", json.dumps(record, ensure_ascii=True, allow_nan=False))
                hosted_diagnostics.add_to_archive(archive, session_id)
            output.seek(0)
            response = send_file(output, mimetype="application/zip", as_attachment=True,
                                 download_name=f"scryraven-{session_id}.zip", max_age=0)
            response.call_on_close(output.close)
            return response
        except Exception:
            output.close()
            raise

    @app.get("/sessions/<session_id>")
    def open_session(session_id):
        return page(session_id)

    def claim(action, session_id=""):
        return forms.claim(request.form.get("form_token", ""), action, session_id, principal=principal())

    def feedback_form(action, session_id, fields):
        if hosted is None:
            abort(404)
        if (set(request.form) != fields
                or any(len(request.form.getlist(name)) != 1 for name in fields)):
            abort(400)
        try:
            claim(action, session_id)
        except _FormError as exc:
            abort(409 if exc.repeated else 403)

    def feedback_failure(exc):
        if exc.code in {"session_not_found", "feedback_turn_not_found", "feedback_not_found"}:
            abort(404)
        raise exc

    @app.post("/sessions/<session_id>/turns/<int:turn_index>/feedback")
    def submit_answer_feedback(session_id, turn_index):
        feedback_form(f"feedback:{turn_index}", session_id, {"form_token", "text"})
        text = request.form["text"]
        try:
            custody.add_feedback(session_id, turn_index, text, owner_id=principal())
        except SessionStoreError as exc:
            if exc.code == "invalid_feedback":
                return page(session_id, status=400, feedback_turn=turn_index,
                            feedback_error=f"Write a comment of 1 to {MAX_ANSWER_FEEDBACK_CHARS:,} characters using plain text.",
                            feedback_text=text[:MAX_ANSWER_FEEDBACK_CHARS])
            feedback_failure(exc)
        return redirect(url_for("open_session", session_id=session_id, notice="feedback_sent",
                                feedback_turn=turn_index, _anchor=f"feedback-{turn_index}"), 303)

    @app.post("/sessions/<session_id>/turns/<int:turn_index>/feedback/<feedback_id>/delete")
    def remove_answer_feedback(session_id, turn_index, feedback_id):
        feedback_form(f"feedback-delete:{turn_index}:{feedback_id}", session_id, {"form_token"})
        try:
            custody.delete_feedback(session_id, turn_index, feedback_id, owner_id=principal())
        except SessionStoreError as exc:
            feedback_failure(exc)
        return redirect(url_for("open_session", session_id=session_id, notice="feedback_removed",
                                feedback_turn=turn_index, _anchor=f"feedback-{turn_index}"), 303)

    def settings_form(names):
        required = {"form_token", *names}
        if (set(request.form) - (required | {"return_session_id"})
                or not required.issubset(request.form)
                or any(len(request.form.getlist(name)) != 1 for name in request.form)):
            abort(400)

    def settings_return_session():
        session_id = request.form.get("return_session_id")
        if session_id:
            try:
                metadata = custody.get_metadata(session_id)
            except SessionStoreError as exc:
                if exc.code == "session_not_found":
                    abort(404)
                raise
            if metadata.owner_id != principal():
                abort(404)
        return session_id

    def settings_redirect(session_id):
        if session_id:
            return redirect(url_for("open_session", session_id=session_id, notice="settings_saved"), 303)
        return redirect(url_for("new_research", notice="settings_saved"), 303)

    @app.post("/sessions/<session_id>/settings/source-language")
    def update_source_language(session_id):
        if (set(request.form) != {"form_token", "citation_language"}
                or any(len(request.form.getlist(name)) != 1 for name in request.form)
                or request.form["citation_language"] not in CITATION_LANGUAGES):
            abort(400)
        try:
            claim("source-language", session_id)
        except _FormError:
            abort(403)
        try:
            custody.set_citation_language(session_id, request.form["citation_language"], owner_id=principal() or None)
        except SessionStoreError as exc:
            if exc.code == "session_not_found":
                abort(404)
            raise
        if request.accept_mimetypes.best == "application/json":
            return jsonify(form_token=forms.issue("source-language", session_id, principal=principal()))
        return settings_redirect(session_id)

    @app.post("/settings/hosted")
    def update_hosted_preferences():
        if hosted is None:
            abort(404)
        settings_form({"research_model", "research_reasoning", "answer_model", "answer_reasoning", "api_processing"})
        claim("hosted-settings")
        return_session_id = settings_return_session()
        try:
            hosted_preferences.save_defaults(request.form)
        except ValueError:
            return page(error="Choose approved models, supported reasoning efforts and Standard or Fast processing.", status=400)
        return settings_redirect(return_session_id)

    @app.post("/settings/processing")
    def update_hosted_processing():
        if hosted is None:
            abort(404)
        settings_form({"api_processing"})
        claim("processing")
        return_session_id = settings_return_session()
        try:
            hosted_preferences.save_processing(principal(), request.form["api_processing"], admin=g.identity.is_admin)
        except ValueError:
            return page(error="Choose Standard or Fast processing.", status=400)
        return settings_redirect(return_session_id)

    @app.post("/settings/billing")
    def update_billing_authorization():
        names = {"form_token", "backend", "authorized"}
        if (set(request.form) != names or any(len(request.form.getlist(name)) != 1 for name in names)
                or request.form.get("backend") not in BILLED_BACKENDS
                or request.form.get("authorized") not in {"0", "1"}):
            abort(400)
        claim("billing")
        custody.set_billing_authorization(request.form["backend"], request.form["authorized"] == "1")
        if request.accept_mimetypes.best == "application/json":
            return jsonify(billing_authorizations=custody.get_billing_authorizations(),
                           form_token=forms.issue("billing"))
        return redirect(url_for("new_research"), 303)

    @app.post("/transcribe")
    @app.post("/sessions/<session_id>/transcribe")
    def transcribe_question(session_id=None):
        try:
            forms.claim(request.headers.get("X-Form-Token", ""), "dictation", session_id or "",
                        replayable=True, principal=principal())
        except _FormError:
            return jsonify(error="Reopen this conversation to use dictation."), 403
        if session_id and hosted is None:
            try:
                custody.get_metadata(session_id)
            except SessionStoreError as exc:
                if exc.code == "session_not_found":
                    abort(404)
                raise
        if not dictation.available():
            return jsonify(error=dictation.API_UNAVAILABLE), 503
        try:
            audio = request.get_data(cache=False)
            dictation.validate_audio(audio)
            if hosted is None and not custody.get_billing_authorizations()["openai"]:
                return jsonify(error=dictation.BILLING_REQUIRED), 403
            with transcription_slots.reserve(principal()):
                text = dictation.transcribe(audio)
        except dictation.TranscriptionError as exc:
            return jsonify(error=str(exc)), exc.status
        if not text:
            return jsonify(error="No speech was transcribed. Try recording again."), 422
        return jsonify(text=text)

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
        language = request.form.get("citation_language", None if session_id else "en")
        if session_id is None and language in CITATION_LANGUAGES:
            g.new_citation_language = language
        try:
            revision = forms.claim(request.form.get("form_token", ""), "ask", session_id or "", replayable=True,
                                   principal=principal())
        except _FormError:
            return page(session_id, question=question, status=409,
                        error="This form has expired. Review your question and submit it again.")
        if not question:
            return page(session_id, error="Write a research question to begin.", status=400)
        if len(question) > 20000:
            return page(session_id, question=question, error="Keep the question within 20,000 characters.", status=400)
        if language is not None and language not in CITATION_LANGUAGES:
            return page(session_id, question=question, error="Choose a citation explanation language.", status=400)
        key = request.form.get("idempotency_key", "") or request.form.get("form_token", "")
        if hosted is not None:
            key = sha256((principal() + "\0" + key).encode()).hexdigest()
        try:
            if hosted is not None:
                allowed_fields = {"form_token", "idempotency_key", "question", "citation_language", "retained_image_ids",
                                  "api_processing"}
                if (set(request.form) - allowed_fields
                        or any(len(request.form.getlist(name)) > 1 for name in allowed_fields - {"retained_image_ids"})):
                    raise ValueError("invalid_run_settings")
                settings = current_hosted_settings()
                if "api_processing" in request.form:
                    from dataclasses import replace
                    settings = replace(settings, api_processing=request.form["api_processing"])
                accepted = custody.find_submission(key, owner_id=principal())
                if (accepted is not None and accepted.run_settings is not None
                        and ("api_processing" not in request.form
                             or request.form["api_processing"] == accepted.run_settings.api_processing)):
                    # A lost-response replay still names the original accepted
                    # snapshot after defaults change. accept_job compares the
                    # complete question/files/context fingerprint as usual.
                    settings = accepted.run_settings
            else:
                settings = settings_from_form(request.form, initial_settings)
            require_billing_authorization(settings.backend)
            documents, images = read_attachments()
            job = jobs.submit(question, session_id=session_id, revision=revision,
                              idempotency_key=key, documents=documents, images=images,
                              retained_image_ids=tuple(request.form.getlist("retained_image_ids")),
                              citation_language=language, run_settings=settings,
                              remember_settings=hosted is None, **admission_identity())
        except (ValueError, ModelError) as exc:
            return page(session_id, question=question, status=400,
                        error=RUN_SETTINGS_ERRORS.get(str(exc), RUN_SETTINGS_ERRORS["invalid_run_settings"]))
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
                "research_queue_full": "The research queue is full. Your question is kept below; try again shortly.",
                "submission_conflict": "An earlier version of this question is already saved. This edited draft was not sent.",
                "submission_quota_exceeded": "Your daily submission limit has been reached. Try again after midnight UTC.",
            }
            response = app.make_response(page(session_id, question=question,
                status=429 if exc.code == "submission_quota_exceeded" else 409,
                error=messages.get(exc.code, "The question could not be accepted. It is kept below; try again.")))
            if exc.code == "submission_conflict":
                accepted = custody.find_submission(key, **({"owner_id": principal()} if hosted is not None else {}))
                if accepted:
                    response.headers["X-ScryRaven-Submission-Conflict"] = "1"
                    response.headers["X-ScryRaven-Submission-Location"] = url_for("open_session", session_id=accepted.session_id)
            return response
        return redirect(url_for("open_session", session_id=job.session_id, _anchor="research-status"), 303)

    @app.get("/jobs/status")
    def job_status():
        own_sessions = visible_sessions()
        allowed = custody.list_sessions() if hosted is not None and g.identity.is_admin else own_sessions
        visible_ids = {item.session_id for item in allowed}
        owned_ids = {item.session_id for item in own_sessions if item.owner_id == (principal() or None)}
        latest = job_summaries(jobs.list(), visible_ids, owned_ids)
        return jsonify(jobs=list(latest.values()))

    @app.post("/sessions/<session_id>/jobs/<job_id>/viewed")
    def acknowledge_answer(session_id, job_id):
        if set(request.form) != {"form_token"} or len(request.form.getlist("form_token")) != 1:
            abort(400)
        try:
            forms.claim(request.form["form_token"], f"view-answer:{job_id}", session_id,
                        replayable=True, principal=principal())
        except _FormError:
            abort(403)
        try:
            custody.acknowledge_completion(session_id, job_id, owner_id=principal() or None)
        except SessionStoreError as exc:
            if exc.code == "job_not_found":
                abort(404)
            raise
        return "", 204

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
        try:
            if previous.run_settings is not None:
                if hosted is not None:
                    from scryraven.hosted_preferences import validate_hosted_settings
                    validate_hosted_settings(previous.run_settings)
                require_billing_authorization(previous.run_settings.backend)
            job = jobs.retry(job_id, idempotency_key=request.form.get("form_token", ""), **admission_identity())
        except (ModelError, ValueError) as exc:
            return page(session_id, question=previous.question, status=400,
                        error=RUN_SETTINGS_ERRORS.get(str(exc), RUN_SETTINGS_ERRORS["invalid_run_settings"]))
        except SessionStoreError as exc:
            if exc.code == "submission_quota_exceeded":
                return page(session_id, question=previous.question, status=429,
                            error="Your daily submission limit has been reached. Try again after midnight UTC.")
            if exc.code == "historical_run_settings_unknown":
                return page(session_id, question=previous.question, status=409,
                            error=RUN_SETTINGS_ERRORS[exc.code])
            raise
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
        if request.endpoint == "transcribe_question":
            return jsonify(error=f"Record up to {dictation.MAX_SECONDS} seconds at a time."), 413
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
