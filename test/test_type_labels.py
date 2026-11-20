"""dcterms:type values are URI references; the list lookup needs their label."""

from data_2_dasch import extract_listvalueiri_from_value, value_labels

TYPE_LIST = [
    {
        "rdfs:label": "DCMI Type",
        "knora-api:hasSubListNode": [
            {"@id": "http://rdfh.ch/lists/0123/image", "rdfs:label": "image"},
        ],
    }
]


def test_value_labels_uses_o_label_for_uri_values():
    props = [{"@id": "http://purl.org/dc/dcmitype/Image", "o:label": "Image"}]
    assert value_labels(props) == ["Image"]


def test_type_lookup_ignores_case():
    iri = extract_listvalueiri_from_value("Image", "type", TYPE_LIST)
    assert iri == "http://rdfh.ch/lists/0123/image"
