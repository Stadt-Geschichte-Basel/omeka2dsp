import pytest
import requests
from typer.testing import CliRunner

from omeka2dsp.cli import app, read_ids

REQUIRED = ("API_HOST", "INGEST_HOST", "PROJECT_SHORT_CODE", "DSP_USER", "DSP_PWD")


def no_network(*args, **kwargs):
    pytest.fail("network access without credentials")


@pytest.mark.parametrize("command", [["sync"], ["add-text-class"]])
def test_missing_credentials_stop_before_network(monkeypatch, tmp_path, command):
    """Safety rule 6."""
    monkeypatch.chdir(tmp_path)  # no .env here
    for name in REQUIRED:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(requests.Session, "request", no_network)
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 1


def test_ids_come_from_options_and_file(tmp_path):
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text("abb1\n\n abb2 \n")
    assert read_ids(["abb3"], ids_file) == {"abb1", "abb2", "abb3"}
    assert read_ids([], None) == frozenset()
