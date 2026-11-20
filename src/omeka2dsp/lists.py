"""List labels to DSP list node IRIs.

`lists` holds the DSP lists as GET /v2/lists/{list-iri} returns them.
"""

from collections.abc import Iterable, Mapping
from typing import Any

# The labels that the project lists have on DSP, by list key.
LIST_LABELS = {
    "temporal": {"Stadt.Geschichte.Basel Era", "Stadt.Geschichte.Basel Epoche"},
    "type": {"DCMI Type", "DCMI Type Vocabulary"},
    "format": {"Internet Media Type"},
    "language": {"ISO 639-1"},
    "license": {"Licenses", "License", "Rights statement"},
}

DspList = Mapping[str, Any]


def _labels(raw: Any) -> set[str]:
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, Mapping):
        value = raw.get("@value") or raw.get("value")
        return {value} if value else set()
    if isinstance(raw, list):
        return {label for entry in raw for label in _labels(entry)}
    return set()


def _names(node: Mapping[str, Any]) -> set[str]:
    names = _labels(node.get("rdfs:label")) | _labels(node.get("labels"))
    return names | {node["name"]} if node.get("name") else names


def find_list(lists: Iterable[DspList], key: str) -> DspList | None:
    wanted = LIST_LABELS.get(key, {key})
    return next((dsp_list for dsp_list in lists if _names(dsp_list) & wanted), None)


def resolve(lists: Iterable[DspList], key: str, label: str) -> str | None:
    """The IRI of the list node with this label. The match ignores case."""
    label = label.strip()
    dsp_list = find_list(lists, key) if label else None
    if dsp_list is None:
        return None
    nodes = dsp_list.get("knora-api:hasSubListNode", [])
    if isinstance(nodes, Mapping):
        nodes = [nodes]
    # DSP labels can differ in case from Omeka ("image" and "Image").
    wanted = label.casefold()
    return next(
        (
            node.get("@id")
            for node in nodes
            if wanted in {name.casefold() for name in _names(node)}
        ),
        None,
    )
