"""Compare the DSP values with the wanted values. Return the changes."""

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from omeka2dsp.fields import Field, Kind, Project, fields_for
from omeka2dsp.lists import DspList
from omeka2dsp.media import FILE_VALUES, PRIVATE_FILE_PERMISSIONS
from omeka2dsp.values import (
    Entry,
    OmekaRecord,
    dsp_entries,
    dsp_value,
    entry_key,
    wanted,
)

Action = Literal["create", "update", "delete"]


class Change(BaseModel):
    """One value change. A delete holds the DSP value, so the log can show it."""

    model_config = ConfigDict(frozen=True)

    field: str
    action: Action
    value_type: str
    value: str | Entry | None = None
    value_id: str | None = None


class Plan(BaseModel):
    model_config = ConfigDict(frozen=True)

    changes: tuple[Change, ...] = ()
    warnings: tuple[str, ...] = ()


def _scalar(field: Field, have: list[Entry], want: tuple) -> list[Change]:
    entry = have[0] if have else {}
    old, new = dsp_value(entry) or "", want[0] if want else ""
    value_id = entry.get("@id")
    if old == new:
        return []
    if not old:
        return [
            Change(
                field=field.prop,
                action="create",
                value_type=field.value_type,
                value=new,
            )
        ]
    action: Action = "delete" if not new else "update"
    return [
        Change(
            field=field.prop,
            action=action,
            value_type=field.value_type,
            value=old if action == "delete" else new,
            value_id=value_id,
        )
    ]


def _many(field: Field, have: list[Entry], want: tuple, deletes: bool) -> list[Change]:
    ids = {value: entry.get("@id") for entry in have if (value := dsp_value(entry))}
    creates = [
        Change(field=field.prop, action="create", value_type=field.value_type, value=v)
        for v in sorted(set(want) - ids.keys())
    ]
    removes = [
        Change(
            field=field.prop,
            action="delete",
            value_type=field.value_type,
            value=v,
            value_id=ids[v],
        )
        for v in sorted(ids.keys() - set(want))
    ]
    return creates + (removes if deletes else [])


def _text(field: Field, have: list[Entry], want: tuple[Entry, ...]) -> list[Change]:
    """Changes that make the DSP text entries equal to the wanted entries.

    A removed value next to a new one becomes an update of the old value. DSP
    keeps the value history, and properties with cardinality 0-1 (isPartOf)
    do not accept a second value.
    """
    old = {entry_key(e): e for e in have}
    new = {entry_key(e): e for e in want}
    creates = [new[k] for k in sorted(new.keys() - old.keys())]
    deletes = [old[k] for k in sorted(old.keys() - new.keys())]
    pairs = min(len(creates), len(deletes))

    def change(action: Action, value: Entry, value_id: str | None = None) -> Change:
        return Change(
            field=field.prop,
            action=action,
            value_type=field.value_type,
            value=value,
            value_id=value_id,
        )

    return (
        [change("update", n, o.get("@id")) for n, o in zip(creates, deletes)]
        + [change("create", n) for n in creates[pairs:]]
        + [change("delete", o, o.get("@id")) for o in deletes[pairs:]]
    )


def plan(
    project: Project,
    record: OmekaRecord,
    resource: Mapping[str, Any],
    lists: Sequence[DspList],
) -> Plan:
    """The changes that make the DSP resource equal to the Omeka record."""
    changes: list[Change] = []
    warnings: list[str] = []
    resource_class = project.local(resource.get("@type", ""))
    for field in fields_for(resource_class):
        if field.create_only:
            continue
        have = dsp_entries(resource, project.name(field.prop))
        want = wanted(field, record, lists)
        key = field.list_key
        for label in want.unresolved:
            # An unresolved label is not an absent value: keep the DSP value.
            kept = "no type deleted" if field.many else "DSP value kept"
            warnings.append(f"{field.prop}: '{label}' is not in list '{key}'; {kept}")
        if field.kind is Kind.RICH_TEXT:
            changes += _text(field, have, want.values)  # ty: ignore[invalid-argument-type]
        elif field.many:
            changes += _many(field, have, want.values, deletes=not want.unresolved)
        elif not want.unresolved:
            changes += _scalar(field, have, want.values)
    return Plan(changes=tuple(changes), warnings=tuple(warnings))


def _permission_pairs(permissions: str) -> set[tuple[str, str]]:
    pairs = set()
    for part in (permissions or "").split("|"):
        if " " in part:
            code, groups = part.strip().split(" ", 1)
            pairs.update((code, group.strip()) for group in groups.split(","))
    return pairs


def file_permission_changes(
    resource: Mapping[str, Any], private: bool
) -> list[tuple[str, Entry]]:
    """The file values of a private media that are not yet restricted."""
    if not private:
        return []
    wanted_pairs = _permission_pairs(PRIVATE_FILE_PERMISSIONS)
    return [
        (prop, value)
        for prop, _ in FILE_VALUES.values()
        for value in dsp_entries(resource, prop)
        if _permission_pairs(value.get("knora-api:hasPermissions", "")) != wanted_pairs
    ]
