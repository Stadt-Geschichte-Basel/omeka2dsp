"""The Omeka-to-DSP mapping. Payload and sync both read FIELDS."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

PARENT = "Parent"
MEDIA = frozenset({"Image", "Document", "Text", "ResourceWithoutMedia"})
ALL = frozenset({PARENT, *MEDIA})


class Kind(StrEnum):
    TEXT = "text"
    RICH_TEXT = "rich text"
    LIST = "list"
    EMPTY = "always empty"
    LINK = "link"


VALUE_TYPES = {
    Kind.TEXT: "knora-api:TextValue",
    Kind.RICH_TEXT: "knora-api:TextValue",
    Kind.LIST: "knora-api:ListValue",
    Kind.EMPTY: "knora-api:ListValue",
    Kind.LINK: "knora-api:LinkValue",
}


class Field(BaseModel):
    """One DSP property and the Omeka term that fills it."""

    model_config = ConfigDict(frozen=True)

    prop: str
    term: str | None
    kind: Kind
    classes: frozenset[str]
    list_key: str | None = None
    many: bool = False
    create_only: bool = False
    # A create payload has this property even when the value is empty.
    required: bool = False
    # Legacy form of hasAbstract: ";" becomes "&#59" (see docs/datamodel).
    semicolon_entity: bool = False

    @property
    def value_type(self) -> str:
        return VALUE_TYPES[self.kind]


def _text(prop: str, term: str, classes=MEDIA, **options) -> Field:
    return Field(prop=prop, term=term, kind=Kind.TEXT, classes=classes, **options)


def _rich(prop: str, term: str, classes=MEDIA) -> Field:
    return Field(prop=prop, term=term, kind=Kind.RICH_TEXT, classes=classes)


def _list(prop: str, term: str, key: str, classes=MEDIA, many=False) -> Field:
    return Field(
        prop=prop, term=term, kind=Kind.LIST, classes=classes, list_key=key, many=many
    )


FIELDS: tuple[Field, ...] = (
    _text("hasIdentifier", "dcterms:identifier", ALL, create_only=True, required=True),
    _text("hasTitle", "dcterms:title", ALL, required=True),
    _text("hasDescription", "dcterms:description", ALL),
    _list("hasTemporalList", "dcterms:temporal", "temporal", ALL),
    _list("hasLanguageList", "dcterms:language", "language", ALL),
    # Subjects are not migrated (issue #7). Sync deletes old values.
    Field(prop="hasSubjectList", term=None, kind=Kind.EMPTY, classes=ALL),
    _rich("isPartOf", "dcterms:isPartOf", frozenset({PARENT})),
    _rich("hasCreator", "dcterms:creator"),
    _rich("hasPublisher", "dcterms:publisher"),
    _rich("hasSource", "dcterms:source"),
    _rich("hasRelation", "dcterms:relation"),
    _text("hasDate", "dcterms:date"),
    _text("hasExtent", "dcterms:extent"),
    _text("hasRights", "dcterms:rights"),
    _text("hasAbstract", "dcterms:abstract", semicolon_entity=True),
    _list("hasTypeList", "dcterms:type", "type", many=True),
    _list("hasFormatList", "dcterms:format", "format"),
    _list("hasLicenseList", "dcterms:license", "license"),
    Field(
        prop="linkToParentObject",
        term=None,
        kind=Kind.LINK,
        classes=MEDIA,
        create_only=True,
    ),
)


def fields_for(resource_class: str) -> tuple[Field, ...]:
    return tuple(field for field in FIELDS if resource_class in field.classes)


class Project(BaseModel):
    """The DSP project and ontology that the payloads use."""

    model_config = ConfigDict(frozen=True)

    iri: str
    shortcode: str
    ontology_name: str
    ontology_iri: str

    @property
    def prefix(self) -> str:
        return f"{self.ontology_name}:"

    def name(self, local: str) -> str:
        return f"{self.prefix}{local}"

    def local(self, name: str) -> str:
        return name.removeprefix(self.prefix)
