import pytest
from pydantic import ValidationError

from omeka2dsp.settings import Settings

REQUIRED = {
    "API_HOST": "https://api.test.com",
    "INGEST_HOST": "https://ingest.test.com",
    "PROJECT_SHORT_CODE": "TEST",
    "DSP_USER": "user@test.com",
    "DSP_PWD": "secret",
}


@pytest.fixture
def env(monkeypatch):
    for name in REQUIRED:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_defaults_and_secret(env):
    for name, value in REQUIRED.items():
        env.setenv(name, value)
    settings = Settings(_env_file=None)
    assert settings.ontology_name == "SGB" and settings.http_timeout == 30
    assert "secret" not in repr(settings)


@pytest.mark.parametrize("value", [None, "", "  "])
def test_missing_or_empty_required_value_fails(env, value):
    for name, setting in REQUIRED.items():
        env.setenv(name, setting)
    if value is None:
        env.delenv("DSP_PWD")
    else:
        env.setenv("DSP_PWD", value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
