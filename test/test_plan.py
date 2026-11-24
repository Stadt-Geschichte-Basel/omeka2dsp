from omeka2dsp.fields import Project
from omeka2dsp.media import PRIVATE_FILE_PERMISSIONS, PUBLIC_FILE_PERMISSIONS
from omeka2dsp.plan import file_permission_changes, plan
from omeka2dsp.values import OmekaRecord

PROJECT = Project(iri="p", shortcode="0001", ontology_name="SGB", ontology_iri="o")
LISTS = [
    {
        "rdfs:label": "ISO 639-1",
        "knora-api:hasSubListNode": [{"@id": "iri-de", "rdfs:label": "de"}],
    },
    {
        "rdfs:label": "DCMI Type",
        "knora-api:hasSubListNode": [{"@id": "iri-image", "rdfs:label": "Image"}],
    },
]
DOI = {"@id": "https://doi.org/10.21255/sgb-04-283636", "o:label": "Band 4"}


def listvalue(iri, value_id):
    return {
        "@id": value_id,
        "@type": "knora-api:ListValue",
        "knora-api:listValueAsListNode": {"@id": iri},
    }


def text(value, value_id="v1"):
    return {
        "@id": value_id,
        "@type": "knora-api:TextValue",
        "knora-api:valueAsString": value,
    }


def changes(resource, raw, cls="Parent"):
    result = plan(
        PROJECT, OmekaRecord.parse(raw), {"@type": f"SGB:{cls}", **resource}, LISTS
    )
    return [(c.field, c.action, c.value, c.value_id) for c in result.changes]


def test_equal_values_need_no_change():
    resource = {"SGB:hasTitle": text("T"), "SGB:hasIdentifier": text("x", "v0")}
    assert changes(resource, {"dcterms:title": [{"@value": "T"}]}) == []


def test_scalar_create_update_delete():
    assert changes({}, {"dcterms:title": [{"@value": "T"}]}) == [
        ("hasTitle", "create", "T", None)
    ]
    assert changes(
        {"SGB:hasTitle": text("A")}, {"dcterms:title": [{"@value": "B"}]}
    ) == [("hasTitle", "update", "B", "v1")]
    assert changes({"SGB:hasTitle": text("A")}, {}) == [
        ("hasTitle", "delete", "A", "v1")
    ]


def test_unresolved_list_label_keeps_dsp_value():
    """Safety rule 1."""
    resource = {"SGB:hasLanguageList": listvalue("iri-de", "v1")}
    result = plan(
        PROJECT,
        OmekaRecord.parse({"dcterms:language": [{"@value": "xx"}]}),
        {"@type": "SGB:Parent", **resource},
        LISTS,
    )
    assert result.changes == ()
    assert "'xx' is not in list 'language'" in result.warnings[0]


def test_uri_only_list_value_keeps_dsp_value():
    resource = {"SGB:hasLanguageList": listvalue("iri-de", "v1")}
    uri = {"dcterms:language": [{"@id": "http://id.loc.gov/de", "o:label": "German"}]}
    result = plan(
        PROJECT, OmekaRecord.parse(uri), {"@type": "SGB:Parent", **resource}, LISTS
    )
    assert result.changes == ()
    assert "'German' is not in list 'language'" in result.warnings[0]


def test_absent_list_value_still_deletes():
    resource = {"SGB:hasLanguageList": listvalue("iri-de", "v1")}
    assert changes(resource, {}) == [("hasLanguageList", "delete", "iri-de", "v1")]


def test_unresolved_type_label_blocks_type_deletions():
    """Safety rule 2."""
    resource = {"SGB:hasTypeList": [listvalue("iri-old", "v1")]}
    types = [{"@id": "u1", "o:label": "Image"}, {"@id": "u2", "o:label": "Nope"}]
    assert changes(resource, {"dcterms:type": types}, "Image") == [
        ("hasTypeList", "create", "iri-image", None)
    ]
    assert changes(resource, {"dcterms:type": types[:1]}, "Image") == [
        ("hasTypeList", "create", "iri-image", None),
        ("hasTypeList", "delete", "iri-old", "v1"),
    ]


def test_subjects_are_not_synced():
    """Issue #19: the ontology has no hasSubjectList."""
    resource = {"SGB:hasSubjectList": [listvalue("iri-s", "v1")]}
    assert changes(resource, {"dcterms:subject": [{"@value": "Stadt"}]}) == []


def test_plain_citation_becomes_link_by_update():
    [(field, action, value, value_id)] = changes(
        {"SGB:isPartOf": text("x")}, {"dcterms:isPartOf": [DOI]}
    )
    assert (field, action, value_id) == ("isPartOf", "update", "v1")
    assert isinstance(value, dict) and "knora-api:textValueAsXml" in value


def test_dsp_canonical_xml_is_no_change():
    from_dsp = {
        "@id": "v1",
        "@type": "knora-api:TextValue",
        "knora-api:textValueAsXml": (
            "<?xml version='1.0' encoding='UTF-8'?>\n<text>"
            '<a href="https://doi.org/10.21255/sgb-04-283636">Band 4</a></text>'
        ),
    }
    assert changes({"SGB:isPartOf": from_dsp}, {"dcterms:isPartOf": [DOI]}) == []


def test_text_leftovers_are_create_or_delete():
    resource = {"SGB:hasRelation": [text("a", "v0"), text("b", "v1")]}
    found = changes(resource, {"dcterms:relation": [{"@value": "c"}]}, "Image")
    assert sorted(action for _, action, _, _ in found) == ["delete", "update"]


def file_resource(permissions):
    return {
        "knora-api:hasStillImageFileValue": {
            "@id": "v",
            "@type": "knora-api:StillImageFileValue",
            "knora-api:hasPermissions": permissions,
        }
    }


PUBLIC = (
    "CR knora-admin:ProjectAdmin|D knora-admin:ProjectMember"
    "|V knora-admin:KnownUser,knora-admin:UnknownUser"
)


def test_restricted_file_with_public_permissions_needs_change():
    found = file_permission_changes(file_resource(PUBLIC), restricted=True)
    assert [permissions for _, _, permissions in found] == [PRIVATE_FILE_PERMISSIONS]


def test_public_file_with_restricted_permissions_needs_change():
    restricted = file_resource(PRIVATE_FILE_PERMISSIONS)
    found = file_permission_changes(restricted, restricted=False)
    assert [permissions for _, _, permissions in found] == [PUBLIC_FILE_PERMISSIONS]


def test_correct_file_permissions_need_no_change():
    restricted = file_resource(PRIVATE_FILE_PERMISSIONS)
    assert file_permission_changes(restricted, restricted=True) == []
    # A public file keeps its default permissions.
    assert (
        file_permission_changes(file_resource("V knora-admin:UnknownUser"), False) == []
    )
