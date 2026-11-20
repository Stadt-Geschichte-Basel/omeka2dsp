"""Media class, privacy, placeholder, and ingest file name."""

import hashlib
import urllib.parse
from pathlib import PurePosixPath

from omeka2dsp.values import OmekaRecord, first_literal

WITHOUT_MEDIA = "ResourceWithoutMedia"

# DSP stores these formats in SIPI. DSP v40 rejects text/csv as a
# DocumentFileValue, so text and data files go to the Text class.
FORMAT_CLASSES = {
    **dict.fromkeys(
        ("image/tiff", "image/jpg", "image/jpeg", "image/png", "image/gif"), "Image"
    ),
    "application/pdf": "Document",
    **dict.fromkeys(
        (
            "text/csv",
            "text/plain",
            "text/markdown",
            "application/json",
            "application/geo+json",
        ),
        "Text",
    ),
}

# The file value property and value type for each class with a file.
FILE_VALUES = {
    "Image": ("knora-api:hasStillImageFileValue", "knora-api:StillImageFileValue"),
    "Document": ("knora-api:hasDocumentFileValue", "knora-api:DocumentFileValue"),
    "Text": ("knora-api:hasTextFileValue", "knora-api:TextFileValue"),
}

# Private media keep public metadata. Only project members can see the file.
PRIVATE_FILE_PERMISSIONS = "CR knora-admin:ProjectAdmin|D knora-admin:ProjectMember"

# Omeka uses one placeholder image for sources that we must not publish.
PLACEHOLDER_SHA256 = frozenset(
    {"2c07e74c08e23923b89470509d095b329e7d77d6bd2e9212b2a773c97ab4c16e"}
)


def media_format(record: OmekaRecord) -> str:
    return first_literal(record.get("dcterms:format"))


def format_class(media_type: str) -> str | None:
    return FORMAT_CLASSES.get(media_type)


def is_placeholder(record: OmekaRecord) -> bool:
    return (
        record.sha256 in PLACEHOLDER_SHA256
        or "platzhalter" in (record.source or "").lower()
    )


def is_placeholder_file(content: bytes) -> bool:
    """True when the bytes are the placeholder, also when o:sha256 is wrong."""
    return hashlib.sha256(content).hexdigest() in PLACEHOLDER_SHA256


def hides_file(record: OmekaRecord) -> bool:
    """Private and placeholder media get metadata only (issues #12, #13, #14)."""
    return is_placeholder(record) or record.private


def media_class(record: OmekaRecord) -> str:
    if hides_file(record):
        return WITHOUT_MEDIA
    return format_class(media_format(record)) or WITHOUT_MEDIA


def ingest_filename(file_url: str) -> str:
    """The file name for DSP ingest, from the Omeka file URL.

    Ingest refuses ".geojson". GeoJSON is JSON (RFC 7946), so the file goes up
    as ".json" with the same bytes.
    """
    name = PurePosixPath(urllib.parse.urlparse(file_url).path).name
    if name.lower().endswith(".geojson"):
        return name[: -len(".geojson")] + ".json"
    return name
