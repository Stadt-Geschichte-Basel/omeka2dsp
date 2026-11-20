from data_2_dasch import (
    PREFIX,
    construct_payload,
    ingest_filename,
    specify_mediaclass,
)


def test_data_files_go_to_text_class():
    """DSP v40 rejects text/csv as DocumentFileValue (live test on rdu-13)."""
    for mime in ("text/csv", "application/json", "application/geo+json"):
        assert specify_mediaclass(mime) == f"{PREFIX}Text"


def test_pdf_and_images():
    assert specify_mediaclass("application/pdf") == f"{PREFIX}Document"
    assert specify_mediaclass("image/tiff") == f"{PREFIX}Image"
    assert specify_mediaclass("") == f"{PREFIX}ResourceWithoutMedia"


def test_text_payload_has_text_file_value():
    payload = construct_payload({}, f"{PREFIX}Text", "p", [], "parent", "x.csv")
    assert payload["knora-api:hasTextFileValue"] == {
        "@type": "knora-api:TextFileValue",
        "knora-api:fileValueHasFilename": "x.csv",
    }


def test_geojson_is_ingested_as_json():
    """DSP ingest refuses .geojson (live test on rdu-13)."""
    assert ingest_filename("map.geojson") == "map.json"
    assert ingest_filename("data.csv") == "data.csv"
