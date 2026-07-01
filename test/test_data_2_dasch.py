"""
Unit tests for data_2_dasch.py changes
Tests for issues #6, #7, #12, #13, #14
"""

import os
import sys

# Add the scripts directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Import the functions we're testing.
# Override the environment explicitly (not setdefault) so pre-existing values on
# CI or a dev machine cannot make PREFIX differ from "SGB:"; restore afterwards.
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


from data_2_dasch import (  # noqa: E402  # isort: skip  (import after env setup)
    PREFIX,
    build_text_or_uri_values,
    sync_mixed_value_array,
)


def test_prefix_definition():
    """Test that PREFIX is correctly defined (issue #6)"""
    assert PREFIX == "SGB:", f"PREFIX should be 'SGB:' but got '{PREFIX}'"
    print("✓ PREFIX definition test passed")


def test_build_text_or_uri_values_text_only():
    """Test build_text_or_uri_values with text values only (issue #7)"""
    values = ["John Doe", "Jane Smith"]
    result = build_text_or_uri_values(values)

    assert len(result) == 2
    assert all(r["@type"] == "knora-api:TextValue" for r in result)
    assert result[0]["knora-api:valueAsString"] == "John Doe"
    assert result[1]["knora-api:valueAsString"] == "Jane Smith"
    print("✓ build_text_or_uri_values (text only) test passed")


def test_build_text_or_uri_values_uri_only():
    """Test build_text_or_uri_values with URI values only (issue #7)"""
    values = ["https://example.com/person1", "http://example.org/person2"]
    result = build_text_or_uri_values(values)

    assert len(result) == 2
    assert all(r["@type"] == "knora-api:UriValue" for r in result)
    assert (
        result[0]["knora-api:uriValueAsUri"]["@value"] == "https://example.com/person1"
    )
    assert (
        result[1]["knora-api:uriValueAsUri"]["@value"] == "http://example.org/person2"
    )
    print("✓ build_text_or_uri_values (URI only) test passed")


def test_build_text_or_uri_values_mixed():
    """Test build_text_or_uri_values with mixed text and URI values (issue #7)"""
    values = ["John Doe", "https://example.com/person1", "Jane Smith"]
    result = build_text_or_uri_values(values)

    assert len(result) == 3
    assert result[0]["@type"] == "knora-api:TextValue"
    assert result[0]["knora-api:valueAsString"] == "John Doe"
    assert result[1]["@type"] == "knora-api:UriValue"
    assert (
        result[1]["knora-api:uriValueAsUri"]["@value"] == "https://example.com/person1"
    )
    assert result[2]["@type"] == "knora-api:TextValue"
    assert result[2]["knora-api:valueAsString"] == "Jane Smith"
    print("✓ build_text_or_uri_values (mixed) test passed")


def test_build_text_or_uri_values_empty():
    """Test build_text_or_uri_values with empty list"""
    values = []
    result = build_text_or_uri_values(values)

    assert len(result) == 0
    print("✓ build_text_or_uri_values (empty) test passed")


def test_sync_mixed_value_array_no_changes():
    """Test sync_mixed_value_array when arrays are identical"""
    dasch_array = ["John Doe", "https://example.com/person1"]
    omeka_array = ["John Doe", "https://example.com/person1"]

    changes = sync_mixed_value_array("hasCreator", dasch_array, omeka_array)

    assert len(changes) == 0
    print("✓ sync_mixed_value_array (no changes) test passed")


def test_sync_mixed_value_array_additions():
    """Test sync_mixed_value_array with new values to add"""
    dasch_array = ["John Doe"]
    omeka_array = ["John Doe", "https://example.com/person1", "Jane Smith"]

    changes = sync_mixed_value_array("hasCreator", dasch_array, omeka_array)

    assert len(changes) == 2
    creates = [c for c in changes if c["type"] == "create"]
    assert len(creates) == 2

    # Check that URI and text types are correctly identified
    uri_creates = [c for c in creates if c["prop_type"] == "UriValue"]
    text_creates = [c for c in creates if c["prop_type"] == "TextValue"]
    assert len(uri_creates) == 1
    assert len(text_creates) == 1
    print("✓ sync_mixed_value_array (additions) test passed")


def test_sync_mixed_value_array_deletions():
    """Test sync_mixed_value_array with values to delete"""
    dasch_array = ["John Doe", "https://example.com/person1", "Jane Smith"]
    omeka_array = ["John Doe"]

    changes = sync_mixed_value_array("hasCreator", dasch_array, omeka_array)

    assert len(changes) == 2
    deletes = [c for c in changes if c["type"] == "delete"]
    assert len(deletes) == 2

    # Check that URI and text types are correctly identified
    uri_deletes = [c for c in deletes if c["prop_type"] == "UriValue"]
    text_deletes = [c for c in deletes if c["prop_type"] == "TextValue"]
    assert len(uri_deletes) == 1
    assert len(text_deletes) == 1
    print("✓ sync_mixed_value_array (deletions) test passed")


def test_sync_mixed_value_array_mixed_changes():
    """Test sync_mixed_value_array with both additions and deletions"""
    dasch_array = ["Old Person", "https://old.example.com/person"]
    omeka_array = ["New Person", "https://new.example.com/person"]

    changes = sync_mixed_value_array("hasCreator", dasch_array, omeka_array)

    assert len(changes) == 4  # 2 creates + 2 deletes
    creates = [c for c in changes if c["type"] == "create"]
    deletes = [c for c in changes if c["type"] == "delete"]
    assert len(creates) == 2
    assert len(deletes) == 2
    print("✓ sync_mixed_value_array (mixed changes) test passed")


if __name__ == "__main__":
    print("Running tests for data_2_dasch.py changes...")
    print()

    # Test PREFIX definition (issue #6)
    test_prefix_definition()

    # Test build_text_or_uri_values (issue #7)
    test_build_text_or_uri_values_text_only()
    test_build_text_or_uri_values_uri_only()
    test_build_text_or_uri_values_mixed()
    test_build_text_or_uri_values_empty()

    # Test sync_mixed_value_array (issue #7)
    test_sync_mixed_value_array_no_changes()
    test_sync_mixed_value_array_additions()
    test_sync_mixed_value_array_deletions()
    test_sync_mixed_value_array_mixed_changes()

    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
