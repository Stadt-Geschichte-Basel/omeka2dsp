"""
Test for privacy flag handling (issues #12, #13, #14).

Private media must never have its file uploaded to DASCH. It is kept as a
metadata-only SGB:ResourceWithoutMedia record (see main() in data_2_dasch.py).
These tests exercise the real ``is_media_private`` predicate so they cannot drift
from the production logic.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Override the environment explicitly so importing the module is deterministic;
# restore afterwards.
_TEST_ENV = {
    "ONTOLOGY_NAME": "SGB",
    "API_HOST": "https://api.test.com",
    "PROJECT_SHORT_CODE": "TEST",
    "INGEST_HOST": "https://ingest.test.com",
    "DSP_USER": "test@test.com",
    "DSP_PWD": "testpwd",
}
_PREVIOUS_ENV = {key: os.environ.get(key) for key in _TEST_ENV}
os.environ.update(_TEST_ENV)


def teardown_module():
    for key, previous in _PREVIOUS_ENV.items():
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


from data_2_dasch import is_media_private  # noqa: E402  # isort: skip


def test_public_media_is_not_private():
    media = {"o:is_public": True, "dcterms:identifier": [{"@value": "test1"}]}
    assert is_media_private(media) is False


def test_is_public_false_is_private():
    media = {"o:is_public": False, "dcterms:identifier": [{"@value": "test2"}]}
    assert is_media_private(media) is True


def test_missing_flags_default_to_public():
    media = {"dcterms:identifier": [{"@value": "test3"}]}
    assert is_media_private(media) is False


def test_o_private_true_is_private():
    """Older Omeka exports / some modules use o:private instead of o:is_public."""
    media = {"o:private": True, "dcterms:identifier": [{"@value": "test4"}]}
    assert is_media_private(media) is True


def test_o_private_false_public_stays_public():
    media = {
        "o:private": False,
        "o:is_public": True,
        "dcterms:identifier": [{"@value": "test5"}],
    }
    assert is_media_private(media) is False


if __name__ == "__main__":
    test_public_media_is_not_private()
    test_is_public_false_is_private()
    test_missing_flags_default_to_public()
    test_o_private_true_is_private()
    test_o_private_false_public_stays_public()
    print("Privacy flag tests passed! ✓")
