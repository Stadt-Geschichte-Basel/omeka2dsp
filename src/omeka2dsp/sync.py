"""Connect the parts: sync one item, then its media."""

import logging
import random
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from omeka_s_client import OmekaClient, OmekaError

from omeka2dsp import omeka, payload
from omeka2dsp.dsp import Dsp, DspError, JsonLd, retry_session
from omeka2dsp.fields import MEDIA, PARENT, Project
from omeka2dsp.media import (
    FILE_VALUES,
    format_class,
    hides_file,
    ingest_filename,
    is_placeholder,
    is_placeholder_file,
    media_class,
    media_format,
)
from omeka2dsp.plan import file_permission_changes, plan
from omeka2dsp.preflight import preflight
from omeka2dsp.settings import Settings
from omeka2dsp.values import OmekaRecord, describe

log = logging.getLogger(__name__)

MediaOf = Callable[[OmekaRecord], list[OmekaRecord]]


@dataclass(frozen=True)
class Selection:
    snapshot: Path | None = None
    # None selects all items. An empty set selects no item.
    ids: frozenset[str] | None = None
    sample: int | None = None


@dataclass(frozen=True)
class Options:
    dry_run: bool = False
    recreate: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Context:
    dsp: Dsp
    project: Project
    lists: list[JsonLd]
    ontology: JsonLd
    omeka: OmekaClient
    options: Options = Options()
    # Identifiers of the media that this run synced. A repeat is a duplicate.
    synced_media: set[str] = field(default_factory=set)


class ErrorCount(logging.Handler):
    """Count the log records at level ERROR or higher."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        self.count += 1


def _without_duplicates(records: list[OmekaRecord], kind: str) -> list[OmekaRecord]:
    """Log each duplicate identifier. Return the records that do not use one."""
    found = omeka.duplicates(records)
    for identifier, ids in found.items():
        log.error(f"{identifier}: duplicate identifier in Omeka {kind} {ids}; skipped")
    return [r for r in records if not r.identifiers() & found.keys()]


def load(
    settings: Settings, omeka_client: OmekaClient, selection: Selection
) -> tuple[list[OmekaRecord], MediaOf]:
    """The selected items, and a function that returns the media of an item."""
    if selection.snapshot:
        items, media = omeka.snapshot(selection.snapshot)
        log.info(
            f"Snapshot {selection.snapshot}: {len(items)} items, {len(media)} media"
        )
        items = _without_duplicates(items, "items")
        grouped = omeka.media_by_item(_without_duplicates(media, "media"))

        def media_of(item: OmekaRecord) -> list[OmekaRecord]:
            return grouped.get(item.id, []) if item.id is not None else []

    else:
        items = _without_duplicates(omeka.api_items(settings, omeka_client), "items")

        def media_of(item: OmekaRecord) -> list[OmekaRecord]:
            return omeka.api_media(omeka_client, item)

    if selection.ids is not None:
        items = omeka.select(items, set(selection.ids))
        log.info(f"Selected {len(items)} of {len(selection.ids)} requested ids")
    if selection.sample:
        items = random.sample(items, min(selection.sample, len(items)))
    return items, media_of


def run(
    settings: Settings,
    selection: Selection,
    options: Options,
    session: requests.Session | None = None,
    omeka_client: OmekaClient | None = None,
) -> int:
    """Sync the selected items. Return the number of errors logged."""
    errors = ErrorCount()
    logging.getLogger("omeka2dsp").addHandler(errors)
    try:
        _run(settings, selection, options, session, omeka_client)
    finally:
        logging.getLogger("omeka2dsp").removeHandler(errors)
    return errors.count


def _run(
    settings: Settings,
    selection: Selection,
    options: Options,
    session: requests.Session | None,
    omeka_client: OmekaClient | None,
) -> None:
    session = session if session is not None else retry_session(settings)
    with omeka_client if omeka_client is not None else omeka.client(settings) as client:
        items, media_of = load(settings, client, selection)
        dsp = Dsp.login(settings, session)
        project = dsp.project()
        lists, ontology = dsp.lists(project), dsp.ontology(project)
        context = Context(dsp, project, lists, ontology, client, options)
        if options.dry_run:
            log.info("Dry run: no writes to DSP")
        for item in items:
            sync_item(context, item, media_of)


def _checked(context: Context, label: str, body: JsonLd, record: OmekaRecord) -> bool:
    """Log the preflight problems. Return True when the payload is safe to send."""
    problems = preflight(body, record, context.ontology, context.project.prefix)
    for problem in problems:
        log.error(f"{label}: preflight: {problem}")
    return not problems


def _create(context: Context, label: str, body: JsonLd) -> str | None:
    try:
        iri = context.dsp.create(body)
    except DspError as error:
        log.error(f"{label}: resource creation failed: {error}")
        return None
    log.info(f"{label}: resource created on DaSCH")
    return iri or context.dsp.find(context.project, body["@type"], label)


def _apply_plan(
    context: Context,
    label: str,
    kind: str,
    resource: Mapping[str, Any],
    record: OmekaRecord,
) -> None:
    """Make the DSP resource equal to the Omeka record, one value at a time."""
    result = plan(context.project, record, resource, context.lists)
    for warning in result.warnings:
        log.warning(f"{label}: {warning}")
    if not result.changes:
        log.info(f"{label}: {kind} exists already, no changes")
    for change in result.changes:
        what = f"{change.field} '{describe(change.value)}'"
        if context.options.dry_run:
            log.info(f"{label}: would {change.action} {what}")
            continue
        try:
            context.dsp.change(
                change.action, payload.change(context.project, resource, change)
            )
        except DspError as error:
            log.error(f"{label}: {change.action} of {change.field} failed: {error}")
            continue
        log.info(f"{label}: {change.action}d {what}")


def _restrict_files(
    context: Context, label: str, resource: Mapping[str, Any], hide: bool
) -> None:
    """Hide the file of a private media. Its metadata stays public."""
    for prop, value in file_permission_changes(resource, hide):
        if context.options.dry_run:
            log.info(f"{label}: would restrict file permissions ({prop})")
            continue
        try:
            context.dsp.restrict(
                payload.restrict_file(context.project, resource, prop, value)
            )
        except DspError as error:
            log.error(f"{label}: file permission update failed: {error}")
            continue
        log.info(f"{label}: restricted file permissions ({prop})")


def sync_item(context: Context, item: OmekaRecord, media_of: MediaOf) -> None:
    label, project = item.identifier, context.project
    parent_iri = context.dsp.find(project, project.name(PARENT), label)
    if parent_iri:
        resource = context.dsp.resource(parent_iri)
        _apply_plan(context, label, "object", resource, item)
    else:
        body = payload.create(project, PARENT, item, context.lists)
        if not _checked(context, label, body, item):
            return
        if context.options.dry_run:
            log.info(f"{label}: would create {project.name(PARENT)}")
        else:
            parent_iri = _create(context, label, body)
    if not parent_iri and not context.options.dry_run:
        # Without a parent, the media would have no link: skip them.
        log.error(f"{label}: no parent resource on DSP; media skipped")
        return
    for media in media_of(item):
        sync_media(context, media, parent_iri)


def _find_media(
    context: Context, identifier: str, wanted_class: str
) -> tuple[str | None, str]:
    """Find a media in any media class. Return (IRI, class) or (None, "").

    DSP cannot change the class of a resource. The caller syncs the resource
    or creates it again, and never makes a second record.
    """
    project = context.project
    for candidate in [wanted_class, *sorted(MEDIA - {wanted_class})]:
        iri = context.dsp.find(project, project.name(candidate), identifier)
        if iri:
            return iri, candidate
    return None, ""


def _megabytes(size: int) -> str:
    """The size in MB, with one decimal."""
    return f"{size / 1_000_000:.1f}"


def _ingest(context: Context, label: str, media: OmekaRecord) -> str | None:
    """Download the Omeka file and ingest it. Return the internal file name."""
    url = media.original_url or ""
    name = ingest_filename(url)
    if not name:
        log.error(f"{label}: the file URL '{url}' has no file name")
        return None
    limit = context.dsp.settings.max_ingest_bytes
    if limit is not None and media.size is not None and media.size > limit:
        log.error(
            f"{label}: file is {_megabytes(media.size)} MB, above MAX_INGEST_BYTES; "
            "not ingested"
        )
        return None
    size = media.size
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file"
            context.omeka.download(url, path)
            content = path.read_bytes()
            size = size if size is not None else len(content)
        if is_placeholder_file(content):
            log.error(f"{url}: file is the placeholder image; not uploaded")
            return None
        return context.dsp.ingest(name, content)
    except (OmekaError, OSError, requests.RequestException, DspError) as error:
        shown = f"{_megabytes(size)} MB" if size is not None else "size unknown"
        log.error(f"{label}: file transfer failed ({shown}): {error}")
        return None


def sync_media(context: Context, media: OmekaRecord, parent_iri: str | None) -> None:
    label, project, dry_run = media.identifier, context.project, context.options.dry_run
    if label in context.synced_media:
        log.error(f"{label}: duplicate media identifier in this run; skipped")
        return
    if label:
        context.synced_media.add(label)
    wanted_class = media_class(media)
    hide = hides_file(media)
    if is_placeholder(media):
        log.info(f"{label}: placeholder -> metadata only")
    elif media.private:
        log.info(f"{label}: private media -> metadata only")
    elif format_class(media_format(media)) is None:
        log.warning(
            f"{label}: unsupported or missing media type '{media_format(media)}'; "
            "falling back to ResourceWithoutMedia"
        )

    iri, found_class = _find_media(context, label, wanted_class)
    replace = bool(iri) and found_class != wanted_class
    if replace and label not in context.options.recreate:
        log.warning(
            f"{label}: exists as {project.name(found_class)}, source now maps to "
            f"{project.name(wanted_class)}; syncing values only (use --recreate to fix)"
        )
        replace = False
    if iri and not replace:
        resource = context.dsp.resource(iri)
        # Hide the file first. A failed metadata change must not leave it public.
        _restrict_files(context, label, resource, hide)
        _apply_plan(context, label, "media", resource, media)
        return

    # A new record or a replacement. Check the payload and ingest the file
    # before the erase, so that a failure keeps the old record.
    draft = payload.create(project, wanted_class, media, context.lists, parent_iri)
    if not _checked(context, label, draft, media):
        return
    if dry_run:
        if replace:
            log.info(
                f"{label}: would erase {project.name(found_class)} "
                f"and recreate as {project.name(wanted_class)}"
            )
        else:
            log.info(f"{label}: would create {project.name(wanted_class)}")
        return

    filename = None
    if wanted_class in FILE_VALUES:
        filename = _ingest(context, label, media)
        if not filename:
            log.error(f"{label}: could not ingest the file; nothing changed")
            return
        log.info(f"{label}: ingested as {filename}")

    if replace and iri:
        old = context.dsp.resource(iri)
        try:
            context.dsp.erase(payload.erase(project, old))
        except DspError as error:
            log.error(f"{iri}: erase failed: {error}")
            return
        log.info(f"{label}: erased {project.name(found_class)} {iri}")

    log.info(f"{label}: adding media to {project.name(wanted_class)} ...")
    body = payload.create(
        project, wanted_class, media, context.lists, parent_iri, filename
    )
    if not _create(context, label, body):
        if filename:
            log.error(
                f"{label}: file {filename} is ingested but has no resource on DSP; "
                "ask DaSCH to remove it"
            )
        if replace:
            log.error(
                f"{label}: old record erased, but the new one failed; run again to create it"
            )
