"""
Test for privacy flag handling (issues #12, #13, #14).

Private media must never have its file uploaded to DASCH. It is kept as a
metadata-only SGB:ResourceWithoutMedia record (see main() in data_2_dasch.py).
These tests exercise the real ``is_media_private`` predicate so they cannot drift
from the production logic.

Import path and environment come from conftest.py.
"""

from data_2_dasch import is_media_private


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
