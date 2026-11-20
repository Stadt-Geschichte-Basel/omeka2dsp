"""Placeholder files from Omeka must never reach DSP."""

import hashlib

import data_2_dasch
from data_2_dasch import PREFIX, is_placeholder, media_class_for, upload_file_from_url

PLACEHOLDER = {
    "o:sha256": next(iter(data_2_dasch.PLACEHOLDER_SHA256)),
    "o:source": "sgb-fdp-platzhalter[1].png",
    "o:is_public": True,
    "dcterms:format": [{"property_id": 9, "@value": "image/jpeg"}],
}
REAL = {
    "o:sha256": "abc",
    "o:source": "ABB15043.jpg",
    "dcterms:format": [{"property_id": 9, "@value": "image/jpeg"}],
}


def test_is_placeholder_by_hash_or_name():
    assert is_placeholder(PLACEHOLDER)
    assert is_placeholder({"o:source": "SGB-FDP-Platzhalter.png"})
    assert is_placeholder({"o:sha256": PLACEHOLDER["o:sha256"]})
    assert not is_placeholder(REAL)


def test_public_placeholder_keeps_metadata_only():
    assert media_class_for(PLACEHOLDER) == f"{PREFIX}ResourceWithoutMedia"
    assert media_class_for(REAL) == f"{PREFIX}Image"
    assert media_class_for({**REAL, "o:is_public": False}) == (
        f"{PREFIX}ResourceWithoutMedia"
    )


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def test_upload_refuses_placeholder_bytes(monkeypatch):
    """A wrong o:sha256 in Omeka must not let the placeholder through."""
    content = b"placeholder bytes"
    monkeypatch.setattr(
        data_2_dasch, "PLACEHOLDER_SHA256", {hashlib.sha256(content).hexdigest()}
    )
    monkeypatch.setattr(
        data_2_dasch.requests, "get", lambda *a, **k: FakeResponse(content)
    )

    def no_upload(*args, **kwargs):
        raise AssertionError("placeholder must not be uploaded")

    monkeypatch.setattr(data_2_dasch.requests, "post", no_upload)
    assert upload_file_from_url("https://omeka/files/x.png", "token") is None
