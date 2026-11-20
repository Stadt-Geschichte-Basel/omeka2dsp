"""Omeka values to DSP values. DSP values to comparison keys."""

import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NamedTuple
from xml.sax.saxutils import escape, quoteattr

from pydantic import BaseModel, ConfigDict
from pydantic import Field as Alias

from omeka2dsp.fields import Field, Kind
from omeka2dsp.lists import DspList, resolve

STANDARD_MAPPING = "http://rdfh.ch/standoff/mappings/StandardMapping"
TEXT_ENTRY_KEYS = frozenset(
    {
        "@type",
        "knora-api:valueAsString",
        "knora-api:textValueAsXml",
        "knora-api:textValueHasMapping",
    }
)

# A DSP value as JSON-LD, for example a TextValue entry.
Entry = dict[str, Any]


class OmekaValue(BaseModel):
    """One value of an Omeka property: a literal, or a URI with a label."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    value: str | None = Alias(None, alias="@value")
    id: str | None = Alias(None, alias="@id")
    label: str | None = Alias(None, alias="o:label")


class OmekaRecord(BaseModel):
    """An Omeka item or media, with its Dublin Core values by term."""

    model_config = ConfigDict(frozen=True)

    id: int | None = None
    item_id: int | None = None
    identifier: str = ""
    private: bool = False
    sha256: str | None = None
    source: str | None = None
    original_url: str | None = None
    values: Mapping[str, tuple[OmekaValue, ...]] = {}

    @classmethod
    def parse(cls, raw: Mapping[str, Any]) -> OmekaRecord:
        values = {
            term: tuple(OmekaValue.model_validate(value) for value in entries)
            for term, entries in raw.items()
            if term.startswith("dcterms:") and isinstance(entries, list)
        }
        return cls(
            id=raw.get("o:id"),
            item_id=(raw.get("o:item") or {}).get("o:id"),
            identifier=first_literal(values.get("dcterms:identifier", ())),
            # Omeka has two privacy flags: o:is_public and o:private.
            private=raw.get("o:private") is True
            or raw.get("o:is_public", True) is False,
            sha256=raw.get("o:sha256"),
            source=raw.get("o:source"),
            original_url=raw.get("o:original_url"),
            values=values,
        )

    def get(self, term: str | None) -> tuple[OmekaValue, ...]:
        return self.values.get(term, ()) if term else ()

    def identifiers(self) -> set[str]:
        return {v.value for v in self.get("dcterms:identifier") if v.value is not None}


def first_literal(values: Iterable[OmekaValue]) -> str:
    return next((v.value for v in values if v.value is not None), "")


def labels(values: Iterable[OmekaValue]) -> list[str]:
    """Plain labels: o:label for URI values, else @value."""
    stripped = ((v.label or v.value or "").strip() for v in values)
    return [label for label in stripped if label]


def semicolon_text(values: Sequence[OmekaValue]) -> str:
    """The first value, with ";" as "&#59". URI values become an <a> element."""

    def entity(text: str) -> str:
        return text.replace(";", "&#59")

    texts = [entity(v.value) for v in values if v.value is not None]
    links = [
        f"<a href='{entity(v.id)}'>{entity(v.label or '')}</a>"
        for v in values
        if v.id is not None
    ]
    return next(iter(texts + links), "")


def text_entries(values: Iterable[OmekaValue]) -> list[Entry]:
    """One TextValue for each Omeka value. A URI value becomes a standoff link.

    The link uses the DSP standard mapping, so the label shows and the URI
    (for example a DOI) stays machine-readable.
    """
    entries = []
    for v in values:
        if v.id:
            label = escape((v.label or v.id).strip())
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f"<text><a href={quoteattr(v.id)}>{label}</a></text>"
            )
            entries.append(
                {
                    "@type": "knora-api:TextValue",
                    "knora-api:textValueAsXml": xml,
                    "knora-api:textValueHasMapping": {"@id": STANDARD_MAPPING},
                }
            )
        elif (v.value or "").strip():
            entries.append(
                {
                    "@type": "knora-api:TextValue",
                    "knora-api:valueAsString": (v.value or "").strip(),
                }
            )
    return entries


class Wanted(NamedTuple):
    """The DSP values that a field must have, and the labels without a list node."""

    values: tuple[str | Entry, ...]
    unresolved: tuple[str, ...] = ()


def wanted(field: Field, record: OmekaRecord, lists: Sequence[DspList]) -> Wanted:
    source = record.get(field.term)
    if field.kind is Kind.TEXT:
        text = (
            semicolon_text(source) if field.semicolon_entity else first_literal(source)
        )
        return Wanted((text,) if text else ())
    if field.kind is Kind.RICH_TEXT:
        return Wanted(tuple(text_entries(source)))
    if field.kind is Kind.LIST and field.list_key:
        found = labels(source) if field.many else [first_literal(source)]
        iris = [(label, resolve(lists, field.list_key, label)) for label in found]
        return Wanted(
            tuple(iri for _, iri in iris if iri),
            tuple(label for label, iri in iris if label and not iri),
        )
    return Wanted(())


def entry_key(entry: Mapping[str, Any]) -> tuple:
    """A comparison key for a text entry, from Omeka or from DSP.

    DSP changes the form of standoff XML (declaration, attribute order), so the
    key holds the plain text and the link targets, not the XML string.
    """
    xml = entry.get("knora-api:textValueAsXml")
    if xml:
        root = ET.fromstring(xml.encode("utf-8"))
        hrefs = tuple(sorted(a.get("href", "") for a in root.iter("a")))
        return ("xml", " ".join("".join(root.itertext()).split()), hrefs)
    return ("text", " ".join((entry.get("knora-api:valueAsString") or "").split()))


def describe(value: str | Mapping[str, Any] | None) -> str:
    """A short log form of a value."""
    if isinstance(value, Mapping):
        key = entry_key(value)
        return f"{key[1]} {list(key[2])}" if key[0] == "xml" else key[1]
    return str(value or "")


def dsp_entries(resource: Mapping[str, Any], prop: str) -> list[Entry]:
    entries: Any = resource.get(prop) or []
    return [entries] if isinstance(entries, dict) else list(entries)


def dsp_value(entry: Mapping[str, Any]) -> str | None:
    """The comparable content of a DSP value: text, list node, link, or URI."""
    match entry.get("@type"):
        case "knora-api:TextValue":
            return entry.get("knora-api:valueAsString")
        case "knora-api:ListValue":
            return entry.get("knora-api:listValueAsListNode", {}).get("@id")
        case "knora-api:LinkValue":
            return entry.get("knora-api:linkValueHasTargetIri", {}).get("@id")
        case "knora-api:UriValue":
            return entry.get("knora-api:uriValueAsUri", {}).get("@value")
    return None
