"""Bounded user image custody and real Responses image inputs, never Evidence."""

from __future__ import annotations

import base64
import hashlib
import re
import warnings
from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from scryraven.documents import sanitize_filename

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_SIDE = 4096
MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGES_PER_QUESTION = 4
MAX_ATTACHMENTS_PER_QUESTION = 4
MAX_ATTACHMENT_REQUEST_BYTES = 24 * 1024 * 1024
IMAGE_ID = re.compile(r"I[1-9]\d*\Z")
IMAGE_MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
IMAGE_ERROR_MESSAGES = {
    "image_type_rejected": "Attach a text PDF, PNG, JPEG or WebP image.",
    "image_too_large": "Each image must be 8 MB or smaller.",
    "image_dimensions_exceeded": "Images must be at most 4096 pixels on each side and 16 megapixels.",
    "image_malformed": "That image could not be decoded. Choose a valid PNG, JPEG or WebP image.",
    "image_animated": "Animated images are not supported. Choose a single still image.",
    "attachment_count_exceeded": "Attach at most four files to one question.",
    "attachment_request_too_large": "Attachments for one question must total 24 MB or less.",
    "model_image_input_unsupported": "The selected model does not have supported image input. Choose a supported model before retrying; the image was retained.",
}


class ImageRejected(Exception):
    """Fixed safe code without decoder errors, paths or image content."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PreparedImage:
    filename: str
    media_type: str
    byte_length: int
    sha256: str
    width: int
    height: int
    original_image: bytes = field(repr=False)


@dataclass(frozen=True)
class SessionImage:
    image_id: str
    filename: str
    media_type: str
    byte_length: int
    sha256: str
    created_at: str
    width: int
    height: int
    original_image: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not IMAGE_ID.fullmatch(self.image_id):
            raise ValueError("invalid_session_image")
        try:
            prepared = prepare_image(self.filename, self.media_type, self.original_image)
        except ImageRejected:
            raise ValueError("invalid_session_image") from None
        if any(getattr(prepared, name) != getattr(self, name) for name in (
                "filename", "media_type", "byte_length", "sha256", "width", "height")):
            raise ValueError("invalid_session_image")

    def metadata(self) -> dict:
        return {"image_id": self.image_id, "filename": self.filename,
                "width": self.width, "height": self.height,
                "provenance": "user_provided_image", "independently_verified": False}


def _decoded(data: bytes):
    if not isinstance(data, bytes) or not data:
        raise ImageRejected("image_malformed")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageRejected("image_too_large")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(data))
            if image.format not in IMAGE_MEDIA_TYPES:
                raise ImageRejected("image_type_rejected")
            if not (0 < image.width <= MAX_IMAGE_SIDE and 0 < image.height <= MAX_IMAGE_SIDE
                    and image.width * image.height <= MAX_IMAGE_PIXELS):
                raise ImageRejected("image_dimensions_exceeded")
            if getattr(image, "n_frames", 1) != 1:
                raise ImageRejected("image_animated")
            image.verify()
            image = Image.open(BytesIO(data))
            image.load()
            return image
    except ImageRejected:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageRejected("image_dimensions_exceeded") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, OverflowError):
        raise ImageRejected("image_malformed") from None


def prepare_image(filename: str, media_type: str, data: bytes) -> PreparedImage:
    """Sniff and fully decode content; extension/MIME never grant acceptance."""
    with _decoded(data) as image:
        actual_media = IMAGE_MEDIA_TYPES[image.format]
        claimed_media = media_type.lower().split(";", 1)[0].strip()
        if claimed_media not in {actual_media, "application/octet-stream", ""}:
            raise ImageRejected("image_type_rejected")
        return PreparedImage(sanitize_filename(filename), actual_media, len(data),
                             hashlib.sha256(data).hexdigest(), image.width, image.height, data)


def image_preview(image: SessionImage) -> bytes:
    """A metadata-free, single-frame PNG preview; original bytes remain in custody."""
    with _decoded(image.original_image) as decoded:
        safe = ImageOps.exif_transpose(decoded).convert("RGBA")
        safe.info.clear()
        safe.thumbnail((1024, 1024))
        output = BytesIO()
        safe.save(output, format="PNG")
        return output.getvalue()


def image_input_blocks(images: tuple[SessionImage, ...] | list[SessionImage]) -> list[dict]:
    """Real user-role image blocks with stable custody IDs, not textual substitutes."""
    if len(images) > MAX_IMAGES_PER_QUESTION:
        raise ImageRejected("attachment_count_exceeded")
    if sum(image.byte_length for image in images) > MAX_ATTACHMENT_REQUEST_BYTES:
        raise ImageRejected("attachment_request_too_large")
    blocks = []
    for image in images:
        blocks.extend([
            {"type": "input_text", "text": f"User-provided image {image.image_id}: {image.filename}. Visual observations are not independently verified external facts."},
            {"type": "input_image", "image_url":
                f"data:{image.media_type};base64,{base64.b64encode(image.original_image).decode('ascii')}",
             "detail": "auto"},
        ])
    return blocks


def supports_image_input(model: str) -> bool:
    """Conservative known multimodal models; never switch a selected model or route."""
    return model in {"gpt-6.1-terra", "gpt-6.1-sol", "gpt-6.1-luna", "gpt-6-astra",
                     "gpt-6-sol", "gpt-6-luna", "gpt-4o", "gpt-4.1", "gpt-4.1-mini",
                     "gpt-4.1-nano", "o3", "o4-mini"}
