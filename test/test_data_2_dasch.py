"""
Unit tests for data_2_dasch.py changes
Tests for issues #6, #7, #12, #13, #14

Import path and environment come from conftest.py.
"""

from data_2_dasch import (
    PREFIX,
    build_text_values,
    extract_listvalueiri_from_value,
    sync_mixed_value_array,
)

# The DaSCH license list uses the license URL as the node label (see
# data/data_model_dasch.json), and Omeka's dcterms:license @value is that same
# URL, so the plain label lookup must resolve it to a list node IRI (issue #7).
LICENSE_URLS = {
    "https://creativecommons.org/publicdomain/mark/1.0/": "license_cc_pdm",
    "https://creativecommons.org/publicdomain/zero/1.0/": "license_cc0",
    "https://creativecommons.org/licenses/by/4.0/": "license_cc_by_4",
    "https://creativecommons.org/licenses/by-sa/4.0/": "license_cc_by_sa_4",
    "https://creativecommons.org/licenses/by-nc-sa/4.0/": "license_cc_by_nc_sa_4",
    "http://rightsstatements.org/vocab/InC/1.0/": "license_in_c",
    "http://rightsstatements.org/vocab/InC-RUU/1.0/": "license_in_c_ruu",
}

LICENSE_LIST_FIXTURE = [
    {
        "rdfs:label": "Licenses",
        "knora-api:hasSubListNode": [
            {"@id": f"http://rdfh.ch/lists/0123/{name}", "rdfs:label": url}
            for url, name in LICENSE_URLS.items()
        ],
    }
]


def test_license_urls_resolve_to_list_node_iris():
    """Each license URL from Omeka maps to a DaSCH list node IRI (issue #7)."""
    for url, name in LICENSE_URLS.items():
        iri = extract_listvalueiri_from_value(url, "license", LICENSE_LIST_FIXTURE)
        assert iri == f"http://rdfh.ch/lists/0123/{name}", (
            f"license URL '{url}' should resolve to node '{name}', got '{iri}'"
        )


def test_unknown_license_url_returns_none():
    iri = extract_listvalueiri_from_value(
        "https://example.com/not-a-license/", "license", LICENSE_LIST_FIXTURE
    )
    assert iri is None


def test_prefix_definition():
    """Test that PREFIX is correctly defined (issue #6)"""
    assert PREFIX == "SGB:", f"PREFIX should be 'SGB:' but got '{PREFIX}'"
    print("✓ PREFIX definition test passed")


def test_build_text_values_sends_urls_as_text():
    """The SGB ontology has no UriValue properties: URLs become TextValue."""
    values = ["John Doe", "https://example.com/person1", ""]
    result = build_text_values(values)

    assert [r["@type"] for r in result] == ["knora-api:TextValue"] * 2
    assert [r["knora-api:valueAsString"] for r in result] == [
        "John Doe",
        "https://example.com/person1",
    ]


def test_build_text_values_empty():
    assert build_text_values([]) == []


def test_sync_mixed_value_array_no_changes():
    values = ["John Doe", "https://example.com/person1"]
    assert sync_mixed_value_array("hasCreator", values, list(values)) == []


def test_sync_mixed_value_array_changes_are_text_values():
    dasch_array = ["Old Person", "https://old.example.com/person"]
    omeka_array = ["Old Person", "https://new.example.com/person"]

    changes = sync_mixed_value_array("hasCreator", dasch_array, omeka_array)

    assert {(c["type"], c["value"]) for c in changes} == {
        ("create", "https://new.example.com/person"),
        ("delete", "https://old.example.com/person"),
    }
    assert all(c["prop_type"] == "TextValue" for c in changes)
