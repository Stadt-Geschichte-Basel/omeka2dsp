"""The mapping table in the docs agrees with FIELDS."""

from pathlib import Path

from omeka2dsp.fields import ALL, FIELDS, MEDIA, Field

DOC = Path(__file__).parent.parent / "docs" / "datamodel" / "index.qmd"


def row(field: Field) -> list[str]:
    classes = {ALL: "all", MEDIA: "media"}.get(field.classes) or ", ".join(
        sorted(field.classes)
    )
    kind = (
        field.kind.value + ", many" * field.many + ", create only" * field.create_only
    )
    term = f"`{field.term}`" if field.term else "(parent IRI)"
    return [f"`{field.prop}`", term, kind, classes]


def doc_rows() -> list[list[str]]:
    section = DOC.read_text(encoding="utf-8").split("## Mapping table", 1)[1]
    lines = [line for line in section.splitlines() if line.startswith("| `")]
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]


def test_docs_table_matches_fields():
    assert doc_rows() == [row(field) for field in FIELDS]
