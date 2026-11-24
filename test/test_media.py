from omeka2dsp.media import (
    PLACEHOLDER_SHA256,
    format_class,
    ingest_filename,
    is_placeholder,
    is_placeholder_file,
    media_class,
    restricts_file,
)
from omeka2dsp.values import OmekaRecord

JPEG = [{"property_id": 9, "@value": "image/jpeg"}]
PLACEHOLDER = OmekaRecord.parse(
    {
        "o:sha256": next(iter(PLACEHOLDER_SHA256)),
        "o:source": "sgb-fdp-platzhalter[1].png",
        "o:is_public": True,
        "dcterms:format": JPEG,
    }
)
REAL = {"o:sha256": "abc", "o:source": "ABB15043.jpg", "dcterms:format": JPEG}


def test_data_files_go_to_text_class():
    """DSP v40 rejects text/csv as DocumentFileValue (live test on rdu-13)."""
    for mime in ("text/csv", "application/json", "application/geo+json"):
        assert format_class(mime) == "Text"
    assert format_class("application/pdf") == "Document"
    assert format_class("image/tiff") == "Image"
    assert format_class("") is None


def test_is_placeholder_by_hash_or_name():
    assert is_placeholder(PLACEHOLDER)
    assert is_placeholder(OmekaRecord.parse({"o:source": "SGB-FDP-Platzhalter.png"}))
    assert not is_placeholder(OmekaRecord.parse(REAL))


def test_only_a_placeholder_gets_metadata_only():
    """A private real file keeps its media class (issue #40)."""
    assert media_class(PLACEHOLDER) == "ResourceWithoutMedia"
    assert media_class(OmekaRecord.parse(REAL)) == "Image"
    private = OmekaRecord.parse({**REAL, "o:is_public": False})
    assert media_class(private) == "Image"
    assert restricts_file(private)
    assert not restricts_file(OmekaRecord.parse(REAL))


def test_private_placeholder_is_not_restricted():
    private = PLACEHOLDER.model_copy(update={"private": True})
    assert media_class(private) == "ResourceWithoutMedia"
    assert not restricts_file(private)


def test_placeholder_bytes_are_detected():
    assert not is_placeholder_file(b"real image")


def test_ingest_filename():
    """DSP ingest refuses .geojson (live test on rdu-13)."""
    assert ingest_filename("https://omeka/files/original/map.geojson") == "map.json"
    assert ingest_filename("https://omeka/files/original/data.csv") == "data.csv"
