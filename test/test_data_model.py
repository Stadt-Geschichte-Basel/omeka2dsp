"""The list nodes of the data model match the Omeka values (issue #38)."""

import json
from collections import Counter
from pathlib import Path

import pytest

from omeka2dsp.lists import LIST_LABELS, resolve
from omeka2dsp.values import OmekaValue, labels

MODEL = json.loads(
    (Path(__file__).parent.parent / "data" / "data_model_dasch.json").read_text(
        encoding="utf-8"
    )
)
MODEL_LISTS = {item["name"]: item for item in MODEL["project"]["lists"]}

NEW_NODES = {
    "language": {
        "language_ar": "ar",
        "language_he": "he",
        "language_gsw": "gsw",
        "language_gmh": "gmh",
    },
    "license": {
        "license_cc_by_nc_nd_4": "https://creativecommons.org/licenses/by-nc-nd/4.0/"
    },
    "type": {"type_interactive_resource": "interactive resource"},
    "format": {"format_image_gif": "image/gif"},
}


def label_of(item: dict) -> str:
    """The label of a list or node. The temporal list has German labels only."""
    return next(iter(item["labels"].values()))


def dsp_lists() -> list[dict]:
    """The model lists in the form of GET /v2/lists/{list-iri}."""
    return [
        {
            "rdfs:label": label_of(item),
            "knora-api:hasSubListNode": [
                {
                    "@id": f"iri:{node['name']}",
                    "name": node["name"],
                    "rdfs:label": label_of(node),
                }
                for node in item["nodes"]
            ],
        }
        for item in MODEL["project"]["lists"]
    ]


@pytest.mark.parametrize(
    ("key", "name", "label"),
    [(k, n, lab) for k, nodes in NEW_NODES.items() for n, lab in nodes.items()],
)
def test_new_node_is_in_the_model_and_resolves(key, name, label):
    nodes = {n["name"]: label_of(n) for n in MODEL_LISTS[key]["nodes"]}
    assert nodes[name] == label
    assert resolve(dsp_lists(), key, label) == f"iri:{name}"


@pytest.mark.parametrize("key", LIST_LABELS)
def test_node_names_and_labels_are_unique(key):
    nodes = MODEL_LISTS[key]["nodes"]
    assert max(Counter(n["name"] for n in nodes).values()) == 1
    # The lookup ignores case, so labels must differ in case-folded form.
    assert max(Counter(label_of(n).casefold() for n in nodes).values()) == 1


def test_list_labels_stay_findable():
    # find_list() finds each list by its DSP label. A rename breaks every lookup.
    for key, item in MODEL_LISTS.items():
        if key in LIST_LABELS:
            assert label_of(item) in LIST_LABELS[key]


def test_language_comment_names_iso_639_2():
    comment = MODEL_LISTS["language"]["comments"]["en"]
    assert "ISO 639-2" in comment


def test_omeka_type_label_matches_the_node():
    # Live Omeka: dcterms:type is a URI value with o:label "Interactive Resource".
    value = OmekaValue.model_validate(
        {
            "@id": "http://purl.org/dc/dcmitype/InteractiveResource",
            "o:label": "Interactive Resource",
        }
    )
    assert labels([value]) == ["Interactive Resource"]
    assert resolve(dsp_lists(), "type", labels([value])[0]) == (
        "iri:type_interactive_resource"
    )
