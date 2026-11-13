"""Provider-neutral representations for mechanical source acquisition."""

from dataclasses import dataclass

import requests


def post_provider_request(url, **kwargs):
    """Send one fixed API request, without following provider endpoint redirects."""
    response = requests.post(url, allow_redirects=False, **kwargs)
    if getattr(response, "is_redirect", False):
        raise requests.exceptions.HTTPError(response=response)
    return response


@dataclass(frozen=True, slots=True)
class FetchedMaterial:
    """Readable source material mechanically associated with its requested URL."""

    requested_url: str
    readable_text: str
