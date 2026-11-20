"""Read an sgb-data-validator snapshot directory as plain Omeka records.

The file order matches sgb_validator.snapshots.read_snapshot: a
`_transformed` file wins over a plain file, which wins over a `_raw` file.
"""

import json
from collections import defaultdict
from pathlib import Path

SUFFIXES = ("_transformed", "", "_raw")


def _read_records(directory: Path, name: str) -> list[dict]:
    for suffix in SUFFIXES:
        path = directory / f"{name}{suffix}.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else [data]
    raise FileNotFoundError(f"No {name}*.json in snapshot {directory}")


def load_snapshot(directory: str | Path) -> tuple[list[dict], list[dict]]:
    """Return (items, media) from a snapshot directory."""
    directory = Path(directory)
    return _read_records(directory, "items"), _read_records(directory, "media")


def media_by_item(media: list[dict]) -> dict[int, list[dict]]:
    """Group media records by the o:id of their parent item."""
    grouped: dict[int, list[dict]] = defaultdict(list)
    for record in media:
        item_id = (record.get("o:item") or {}).get("o:id")
        if item_id is not None:
            grouped[item_id].append(record)
    return dict(grouped)


def identifiers(record: dict) -> set[str]:
    return {
        value["@value"]
        for value in record.get("dcterms:identifier", [])
        if "@value" in value
    }


def select(items: list[dict], ids: set[str]) -> list[dict]:
    """Keep the items whose dcterms:identifier is in ids."""
    return [item for item in items if identifiers(item) & ids]
