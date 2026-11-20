"""Each command exits before network access when DSP credentials are missing."""

import sys

import pytest
import requests

import add_text_class
import data_2_dasch
import remove_subject_values


def no_network(*args, **kwargs):
    pytest.fail("network access without credentials")


@pytest.mark.parametrize(
    "module", [data_2_dasch, add_text_class, remove_subject_values]
)
def test_missing_credentials_exit_before_network(monkeypatch, module):
    monkeypatch.setattr(data_2_dasch, "DSP_USER", None)
    monkeypatch.setattr(data_2_dasch, "setup_logging", lambda: None)
    monkeypatch.setattr(requests, "get", no_network)
    monkeypatch.setattr(requests, "post", no_network)
    monkeypatch.setattr(sys, "argv", ["script"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 1
