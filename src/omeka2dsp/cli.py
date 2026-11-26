"""The omeka2dsp command."""

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from omeka2dsp import payload
from omeka2dsp.dsp import Dsp, retry_session
from omeka2dsp.settings import Settings
from omeka2dsp.sync import Options, Selection, run

LOG_FILE = "data_2_dasch.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

log = logging.getLogger(__name__)
app = typer.Typer(no_args_is_help=True, help="Migrate Omeka records to DSP.")


def _settings() -> Settings:
    """Load the settings. Stop before network access when one is missing."""
    try:
        return Settings()
    except ValidationError as error:
        names = sorted({str(e["loc"][0]).upper() for e in error.errors()})
        log.error(f"Missing or empty settings: {', '.join(names)}")
        raise typer.Exit(1) from None


def read_ids(ids: list[str] | None, ids_file: Path | None) -> frozenset[str] | None:
    """The selected identifiers, or None when the command selects no identifiers."""
    if ids is None and ids_file is None:
        return None
    lines = ids_file.read_text(encoding="utf-8").splitlines() if ids_file else []
    return frozenset(i.strip() for i in [*(ids or []), *lines] if i.strip())


@app.command()
def sync(
    snapshot: Annotated[
        Path | None,
        typer.Option(help="Read items and media from this snapshot directory."),
    ] = None,
    ids: Annotated[
        list[str] | None,
        typer.Option("--id", help="Select the item with this dcterms:identifier."),
    ] = None,
    ids_file: Annotated[
        Path | None, typer.Option(help="Select the identifiers in this file.")
    ] = None,
    sample: Annotated[
        int | None, typer.Option(min=1, help="Select this number of random items.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option(help="Check payloads and log changes. Write nothing.")
    ] = False,
    recreate: Annotated[
        list[str] | None,
        typer.Option(help="Erase this media in the wrong class and create it again."),
    ] = None,
    log_file: Annotated[
        Path, typer.Option(help="Write the log to this file. It replaces the old file.")
    ] = Path(LOG_FILE),
) -> None:
    """Sync the items of the item set and their media to DSP."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file, mode="w")],
        force=True,
    )
    # omeka-s-client logs each HTTP request at INFO. The run log needs only failures.
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    selected = read_ids(ids, ids_file)
    if selected is not None and not selected:
        # An empty selection must not become a sync of the full item set.
        log.error("The selection has no identifiers; nothing to sync")
        raise typer.Exit(1)
    settings = _settings()
    selection = Selection(snapshot, selected, sample)
    errors = run(settings, selection, Options(dry_run, frozenset(recreate or [])))
    if errors:
        log.error(f"Run finished with {errors} errors")
        raise typer.Exit(1)


@app.command("add-text-class")
def add_text_class(
    apply: Annotated[bool, typer.Option(help="Send the request.")] = False,
    model: Annotated[Path, typer.Option(help="The DSP data model file.")] = Path(
        "data/data_model_dasch.json"
    ),
) -> None:
    """Add the Text class of the data model to the DSP ontology.

    This needs a DSP user with project-admin rights.
    """
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, force=True)
    settings = _settings()
    dsp = Dsp.login(settings, retry_session(settings))
    project = dsp.project()
    last_modified = dsp.ontology_metadata(project)["knora-api:lastModificationDate"]
    body = payload.text_class(
        json.loads(model.read_text(encoding="utf-8")), project, last_modified
    )
    if not apply:
        typer.echo(json.dumps(body, indent=2, ensure_ascii=False))
        typer.echo("Dry run. Use --apply to create the class.")
        return
    typer.echo(json.dumps(dsp.create_class(body), ensure_ascii=False)[:1000])
