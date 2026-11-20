"""Tests for standoff text entries and private file permissions."""

from dsp_values import (
    PRIVATE_FILE_PERMISSIONS,
    build_text_entries,
    entry_key,
    file_permission_changes,
    sync_text_entries,
)

DOI = {
    "type": "uri",
    "@id": "https://doi.org/10.21255/sgb-04-283636",
    "o:label": "Aufbrüche, Krisen & Transformationen",
}


def test_uri_value_becomes_standoff_link():
    [entry] = build_text_entries([DOI])
    assert entry["@type"] == "knora-api:TextValue"
    assert "valueAsString" not in str(entry)
    assert entry["knora-api:textValueHasMapping"]["@id"].endswith("StandardMapping")
    assert entry_key(entry) == (
        "xml",
        "Aufbrüche, Krisen & Transformationen",
        ("https://doi.org/10.21255/sgb-04-283636",),
    )


def test_literal_value_stays_unformatted():
    [entry] = build_text_entries([{"@value": " Burghartz; Susanna "}])
    assert entry == {
        "@type": "knora-api:TextValue",
        "knora-api:valueAsString": "Burghartz; Susanna",
    }


def test_key_ignores_dsp_canonical_xml_form():
    """DSP returns the XML in a canonical form; the sync must see no change."""
    [wanted] = build_text_entries([DOI])
    from_dsp = {
        "@id": "http://rdfh.ch/4001/x/values/y",
        "@type": "knora-api:TextValue",
        "knora-api:textValueAsXml": (
            "<?xml version='1.0' encoding='UTF-8'?>\n<text>"
            '<a href="https://doi.org/10.21255/sgb-04-283636">'
            "Aufbrüche, Krisen &amp; Transformationen</a></text>"
        ),
    }
    assert sync_text_entries("isPartOf", [from_dsp], [wanted]) == []


def test_sync_replaces_plain_citation_with_link():
    old = {"@id": "v1", "@type": "knora-api:TextValue", "knora-api:valueAsString": "x"}
    changes = sync_text_entries("isPartOf", [old], build_text_entries([DOI]))
    assert [c["type"] for c in changes] == ["update"]
    assert changes[0]["value"]["@id"] == "v1"
    assert "knora-api:textValueAsXml" in changes[0]["value"]


def test_sync_leftovers_are_create_or_delete():
    old = [
        {"@id": f"v{i}", "@type": "knora-api:TextValue", "knora-api:valueAsString": s}
        for i, s in enumerate(["a", "b"])
    ]
    new = build_text_entries([{"@value": "c"}])
    kinds = sorted(c["type"] for c in sync_text_entries("hasRelation", old, new))
    assert kinds == ["delete", "update"]


def file_resource(permissions):
    return {
        "knora-api:hasStillImageFileValue": {
            "@id": "v",
            "@type": "knora-api:StillImageFileValue",
            "knora-api:hasPermissions": permissions,
        }
    }


def test_private_file_with_public_permissions_needs_change():
    public = (
        "CR knora-admin:ProjectAdmin|D knora-admin:ProjectMember"
        "|V knora-admin:KnownUser,knora-admin:UnknownUser"
    )
    assert len(file_permission_changes(file_resource(public), private=True)) == 1


def test_restricted_or_public_media_need_no_change():
    restricted = file_resource(PRIVATE_FILE_PERMISSIONS)
    assert file_permission_changes(restricted, private=True) == []
    assert file_permission_changes(file_resource("V x"), private=False) == []
