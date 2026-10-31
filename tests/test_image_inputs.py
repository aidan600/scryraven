"""Decoded image custody and genuine multimodal role/continuation payloads offline."""

from __future__ import annotations

import base64
import json
from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image, PngImagePlugin

from scryraven.errors import RunError
from scryraven.images import (
    MAX_IMAGE_BYTES,
    ImageRejected,
    SessionImage,
    image_preview,
    prepare_image,
)
from scryraven.model import ModelConfig, ModelRole, OpenAIModel
from scryraven.research import _run_turn


def encoded(format="PNG", size=(64, 32)):
    output = BytesIO()
    with Image.new("RGB", size, "white") as image:
        image.save(output, format=format)
    return output.getvalue()


def session_image(image_id="I1", data=None):
    image = prepare_image("../../unsafe.png", "image/png", data or encoded())
    return SessionImage(image_id=image_id, created_at="2026-10-30T00:00:00+00:00", **asdict(image))


@pytest.mark.parametrize("format,media", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")])
def test_acceptance_uses_actual_decoded_content_and_sanitizes_filename(format, media):
    data = encoded(format)
    prepared = prepare_image("../../harmless.exe", "application/octet-stream", data)
    assert (prepared.filename, prepared.media_type, prepared.width, prepared.height) == (
        "harmless.exe", media, 64, 32)
    assert prepared.original_image == data
    with pytest.raises(ImageRejected, match="image_type_rejected"):
        prepare_image("image.png", "image/gif", data)


@pytest.mark.parametrize("data,code", [
    (b"MZ executable content", "image_malformed"),
    (b"<svg onload='alert(1)'/>", "image_malformed"),
    (b"\x89PNG\r\n\x1a\n", "image_malformed"),
    (encoded()[:40], "image_malformed"),
    (encoded()[:-12], "image_malformed"),
    (encoded("GIF"), "image_type_rejected"),
    (b"x" * (MAX_IMAGE_BYTES + 1), "image_too_large"),
    (encoded(size=(4097, 1)), "image_dimensions_exceeded"),
    (encoded(size=(4096, 4096)), "image_dimensions_exceeded"),
], ids=["executable", "svg", "png-header", "truncated", "missing-end", "gif", "oversize", "wide", "pixels"])
def test_reject_unsupported_malformed_and_bounded_uploads(data, code):
    with pytest.raises(ImageRejected, match=code):
        prepare_image("pretend.png", "image/png", data)


def test_reject_animation_and_preview_has_no_active_content_or_metadata():
    first, second = Image.new("RGB", (8, 8), "red"), Image.new("RGB", (8, 8), "blue")
    output = BytesIO()
    first.save(output, format="PNG", save_all=True, append_images=[second])
    with pytest.raises(ImageRejected, match="image_animated"):
        prepare_image("animation.png", "image/png", output.getvalue())
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "<script>not active image content</script>")
    output = BytesIO()
    first.save(output, format="PNG", pnginfo=metadata)
    image = session_image(data=output.getvalue())
    preview = image_preview(image)
    assert image.original_image == output.getvalue()
    assert b"script" not in preview and b"Comment" not in preview
    with Image.open(BytesIO(preview)) as decoded:
        assert decoded.format == "PNG" and not decoded.info


def test_custody_rejects_corrupt_metadata_without_exposing_bytes():
    image = session_image()
    assert "original_image" not in repr(image)
    for changes in ({"image_id": "../I1"}, {"sha256": "incorrect"}, {"width": 1}):
        with pytest.raises(ValueError, match="invalid_session_image"):
            SessionImage(**{**asdict(image), **changes})


def decision(requests=()):
    return {"briefing": None, "action": "research" if requests else "return",
            "requests": list(requests), "retain": [], "evidence_refs": []}


def answer(text="The attached image contains a red circle and a blue square.", basis="user_images"):
    return {"posture": "supported", "support_basis": basis, "answer": text,
            "missing_information": None, "citation_descriptions": None}


def reply(value):
    return {"status": "completed", "output": [{"type": "message", "role": "assistant",
        "content": [{"type": "output_text", "text": json.dumps(value)}]}]}


def scripted(monkeypatch, outputs, backend="api", config=None):
    payloads, remaining = [], iter(outputs)
    config = config or ModelConfig(ModelRole("gpt-6.1-terra", "medium"), ModelRole("gpt-6.1-sol", "medium"))
    model = OpenAIModel(config, backend="api")

    def dispatch(payload, timeout, **kwargs):
        payloads.append(deepcopy(payload))
        return next(remaining)

    if backend == "api":
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-key")
        monkeypatch.setattr("scryraven.model._api_response",
                            lambda post, payload, token, timeout, **kwargs: dispatch(payload, timeout))
    else:
        from scryraven.chatgpt_plan.transport import plan_payload
        model.backend = "chatgpt_plan"
        model.plan_transport = SimpleNamespace(request=lambda payload, **kwargs: dispatch(plan_payload(payload), **kwargs))
    return model, payloads


def image_blocks(payload):
    return [block for item in payload["input"] for block in item.get("content", [])
            if block.get("type") == "input_image"]


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_actual_image_input_reaches_both_roles_without_becoming_evidence(monkeypatch, backend):
    image = session_image()
    model, payloads = scripted(monkeypatch, [reply(decision()), reply(answer())], backend)
    result = _run_turn("What two colored shapes are in this attached image?", model=model,
                       images=(image,), image_ids=("I1",))
    assert result.image_ids == ("I1",)
    assert not result.evidence and not result.selected_evidence and not result.citations
    assert [payload["model"] for payload in payloads] == ["gpt-6.1-terra", "gpt-6.1-sol"]
    for payload in payloads:
        block, = image_blocks(payload)
        prefix, data = block["image_url"].split(",", 1)
        assert prefix == "data:image/png;base64"
        assert base64.b64decode(data) == image.original_image
        assert block["detail"] == "auto"


def test_research_semantically_reads_retained_image_and_unrelated_turn_does_not_send_it(monkeypatch):
    image = session_image()
    read = {"kind": "read", "target": "I1", "focus": "", "mode": "local",
            "start_char": None, "end_char": None}
    model, payloads = scripted(monkeypatch, [reply(decision([read])), reply(decision()), reply(answer())])
    result = _run_turn("What shapes were in my earlier image?", model=model, images=(image,))
    assert result.image_ids == ("I1",)
    assert [len(image_blocks(payload)) for payload in payloads] == [0, 1, 1]
    initial_text = "".join(block["text"] for item in payloads[0]["input"] if item.get("role") == "user"
                           for block in item["content"] if block["type"] == "input_text")
    assert json.loads(initial_text)["image_catalog"][0]["image_id"] == "I1"
    model, payloads = scripted(monkeypatch, [reply(decision()), reply(answer("Two plus two is four.", "user_premises"))])
    result = _run_turn("Given two plus two, calculate the sum.", model=model, images=(image,))
    assert not result.image_ids and not any(image_blocks(payload) for payload in payloads)


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_answer_retained_image_read_appends_real_image_to_native_continuation(monkeypatch, backend):
    tool = {"status": "completed", "output": [{"type": "function_call", "name": "library_read",
            "call_id": "inspect-image", "arguments": json.dumps({"target": "I1", "focus": "",
            "start_char": None, "end_char": None})}]}
    model, payloads = scripted(monkeypatch, [reply(decision()), tool, reply(answer())], backend)
    result = _run_turn("Describe my previous image", model=model, images=(session_image(),))
    assert [len(image_blocks(payload)) for payload in payloads] == [0, 0, 1]
    assert result.image_ids == ("I1",)
    tools = payloads[1].get("tools", []) or next(
        item["tools"] for item in payloads[1]["input"] if item.get("type") == "additional_tools")
    read_tool = next(tool for tool in tools if tool["name"] == "library_read")
    assert "image by I#" in read_tool["description"]
    assert "actual visual content" in read_tool["description"]
    assert "not external Evidence or citation authority" in read_tool["description"]
    from scryraven.answer_library import LIBRARY_TOOLS
    unchanged = next(tool for tool in LIBRARY_TOOLS if tool["name"] == "library_read")
    assert unchanged["description"].startswith("Read only acquired text")
    assert "I#" not in unchanged["description"]
    output = next(item for item in payloads[-1]["input"] if item.get("type") == "function_call_output")
    assert json.loads(output["output"])["evidence"] is False


def test_image_input_never_switches_an_unsupported_model_or_executes_paid_work(monkeypatch):
    config = ModelConfig(ModelRole("gpt-6.1-terra", "medium"), ModelRole("text-only-unsupported", "medium"))
    model, payloads = scripted(monkeypatch, [], config=config)
    with pytest.raises(RunError, match="model_image_input_unsupported"):
        _run_turn("Inspect", model=model, images=(session_image(),), image_ids=("I1",))
    assert not payloads


def test_image_answer_does_not_gain_external_citation_membership(monkeypatch):
    model, _ = scripted(monkeypatch, [reply(decision()), reply(answer("A verified external fact [E1]."))])
    with pytest.raises(RunError):
        _run_turn("Inspect", model=model, images=(session_image(),), image_ids=("I1",))


def test_user_images_basis_requires_actual_supplied_image(monkeypatch):
    unable = {"posture": "unable", "support_basis": "none", "answer": "No image is available.",
              "missing_information": "an image", "citation_descriptions": None}
    model, payloads = scripted(monkeypatch, [reply(decision()), reply(answer()), reply(unable)])
    result = _run_turn("Inspect", model=model)
    assert result.posture == "unable" and len(payloads) == 3
