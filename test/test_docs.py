"""The tables in the docs agree with the code."""

from pathlib import Path

from omeka2dsp.fields import ALL, FIELDS, MEDIA, Field
from omeka2dsp.settings import Settings

ROOT = Path(__file__).parent.parent
DOC = ROOT / "docs" / "datamodel" / "index.qmd"
README = ROOT / "README.md"


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


def test_readme_settings_table_matches_settings():
    section = README.read_text(encoding="utf-8").split("## Settings", 1)[1]
    section = section.split("\n## ", 1)[0]
    names = [
        line.split("`")[1] for line in section.splitlines() if line.startswith("| `")
    ]
    assert names == [name.upper() for name in Settings.model_fields]
