"""Pure helpers for DSP text values and file permissions."""

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

STANDARD_MAPPING = "http://rdfh.ch/standoff/mappings/StandardMapping"
TEXT_ENTRY_KEYS = {
    "@type",
    "knora-api:valueAsString",
    "knora-api:textValueAsXml",
    "knora-api:textValueHasMapping",
}

# File values on DSP. Private media keep public metadata, but the file must not
# be visible to anonymous (UnknownUser) or logged-in non-members (KnownUser).
FILE_VALUE_PROPERTIES = (
    "knora-api:hasStillImageFileValue",
    "knora-api:hasDocumentFileValue",
)
PRIVATE_FILE_PERMISSIONS = "CR knora-admin:ProjectAdmin|D knora-admin:ProjectMember"


def build_text_entries(props: list[dict]) -> list[dict]:
    """Turn Omeka values into DSP TextValue entries.

    A URI value (@id + o:label) becomes formatted text: <a href> in the DSP
    standard mapping (a StandoffUriTag), so the label shows and the link (e.g. a
    DOI) stays machine-readable. A literal value stays unformatted text.
    """
    entries = []
    for prop in props:
        if prop.get("@id"):
            label = (prop.get("o:label") or prop["@id"]).strip()
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                f"<text><a href={quoteattr(prop['@id'])}>{escape(label)}</a></text>"
            )
            entries.append(
                {
                    "@type": "knora-api:TextValue",
                    "knora-api:textValueAsXml": xml,
                    "knora-api:textValueHasMapping": {"@id": STANDARD_MAPPING},
                }
            )
        elif (prop.get("@value") or "").strip():
            entries.append(
                {
                    "@type": "knora-api:TextValue",
                    "knora-api:valueAsString": prop["@value"].strip(),
                }
            )
    return entries


def _normalise(text: str) -> str:
    return " ".join(text.split())


def entry_key(entry: dict) -> tuple:
    """A comparison key for a text entry, from Omeka or as DSP returns it.

    DSP canonicalises standoff XML (declaration, attribute order, empty tags),
    so we compare the plain text and the link targets, not the XML string.
    """
    xml = entry.get("knora-api:textValueAsXml")
    if xml:
        root = ET.fromstring(xml.encode("utf-8"))
        hrefs = tuple(sorted(a.get("href", "") for a in root.iter("a")))
        return ("xml", _normalise("".join(root.itertext())), hrefs)
    return ("text", _normalise(entry.get("knora-api:valueAsString") or ""))


def dasch_entries(resource: dict, prop: str) -> list[dict]:
    entries = resource.get(prop) or []
    return [entries] if isinstance(entries, dict) else entries


def sync_text_entries(field: str, dasch: list[dict], wanted: list[dict]) -> list:
    """Changes that make the DSP entries equal to the wanted entries.

    A removed value paired with a new one becomes an update of the old value.
    DSP keeps the value history, and properties with cardinality 0-1 (isPartOf)
    do not accept a second value next to the old one.
    """
    have = {entry_key(e): e for e in dasch}
    want = {entry_key(e): e for e in wanted}
    to_create = [want[k] for k in sorted(want.keys() - have.keys())]
    to_delete = [have[k] for k in sorted(have.keys() - want.keys())]
    pairs = min(len(to_create), len(to_delete))

    def change(kind, value):
        return {"field": field, "prop_type": "TextValue", "type": kind, "value": value}

    return (
        [
            change("update", {**new, "@id": old["@id"]})
            for new, old in zip(to_create, to_delete)
        ]
        + [change("create", value) for value in to_create[pairs:]]
        + [change("delete", value) for value in to_delete[pairs:]]
    )


def describe(value) -> str:
    """Short log form of a value: plain strings as is, entries by their key."""
    if isinstance(value, dict):
        key = entry_key(value)
        return f"{key[1]} {list(key[2])}" if key[0] == "xml" else key[1]
    return str(value)


def parse_permissions(permissions: str) -> set[tuple[str, str]]:
    pairs = set()
    for part in (permissions or "").split("|"):
        if " " in part:
            code, groups = part.strip().split(" ", 1)
            pairs.update((code, group.strip()) for group in groups.split(","))
    return pairs


def file_permission_changes(resource: dict, private: bool) -> list[tuple[str, dict]]:
    """File values of a private media resource that are not yet restricted.

    Public media keep the project default permissions, so they need no change.
    """
    if not private:
        return []
    wanted = PRIVATE_FILE_PERMISSIONS
    return [
        (prop, value)
        for prop in FILE_VALUE_PROPERTIES
        for value in dasch_entries(resource, prop)
        if parse_permissions(value.get("knora-api:hasPermissions", ""))
        != parse_permissions(wanted)
    ]
