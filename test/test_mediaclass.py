from data_2_dasch import PREFIX, specify_mediaclass


def test_csv_keeps_metadata_only():
    """DSP v40 rejects text/csv as DocumentFileValue (live test on rdu-13)."""
    assert specify_mediaclass("text/csv") == f"{PREFIX}ResourceWithoutMedia"


def test_pdf_and_images():
    assert specify_mediaclass("application/pdf") == f"{PREFIX}Document"
    assert specify_mediaclass("image/tiff") == f"{PREFIX}Image"
