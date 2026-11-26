# omeka2dsp

omeka2dsp copies the research data of [Stadt.Geschichte.Basel (SGB)](https://stadtgeschichtebasel.ch/) from Omeka S to the [DaSCH Service Platform (DSP)](https://www.dasch.swiss/) for long-term preservation.
It creates new records, changes records that are different, and uploads the media files.

[![Code license](https://img.shields.io/github/license/Stadt-Geschichte-Basel/omeka2dsp.svg)](LICENSE.md)
[![GitHub issues](https://img.shields.io/github/issues/Stadt-Geschichte-Basel/omeka2dsp.svg)](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues)

```mermaid
graph LR
  omeka[Omeka S API or snapshot] --> sync[omeka2dsp sync]
  sync --> dsp[DSP API]
  sync --> ingest[DSP ingest]
```

## Documentation

- [Architecture](docs/architecture/index.qmd): modules, sync flow, and safety rules.
- [Data model](docs/datamodel/index.qmd): DSP classes, lists, and the mapping table.
- [Full run](docs/full-run/index.qmd): steps, run time, and the known DSP ingest errors.

## Setup

You need [uv](https://docs.astral.sh/uv/). uv installs Python 3.15 when it is not on your computer.

```bash
git clone https://github.com/Stadt-Geschichte-Basel/omeka2dsp.git
cd omeka2dsp
uv sync --extra dev
cp example.env .env
```

Then write your values into `.env`.

## Settings

omeka2dsp reads `.env` and the environment.
If a required value is missing, the command stops before it connects to a server.

| Variable             | Required | Default                       | Content                                                           |
| -------------------- | -------- | ----------------------------- | ----------------------------------------------------------------- |
| `API_HOST`           | yes      |                               | DSP API, for example `https://api.dasch.swiss`.                   |
| `INGEST_HOST`        | yes      |                               | DSP ingest service, for example `https://ingest.dasch.swiss`.     |
| `PROJECT_SHORT_CODE` | yes      |                               | DSP project short code, for example `4001`.                       |
| `DSP_USER`           | yes      |                               | DSP user email.                                                   |
| `DSP_PWD`            | yes      |                               | DSP password.                                                     |
| `ONTOLOGY_NAME`      | no       | `SGB`                         | Name of the project ontology on DSP.                              |
| `ITEM_SET_ID`        | no       | `10780`                       | Omeka item set to sync.                                           |
| `OMEKA_API_URL`      | no       | `https://omeka.unibe.ch/api/` | Omeka S API.                                                      |
| `KEY_IDENTITY`       | no       |                               | Omeka API key. Without a key, private items are missing.          |
| `KEY_CREDENTIAL`     | no       |                               | Omeka API key secret.                                             |
| `HTTP_TIMEOUT`       | no       | `30` (seconds)                | Timeout for each request.                                         |
| `INGEST_TIMEOUT`     | no       | `600` (seconds)               | Timeout for each file upload. Use `3600` for files of several GB. |
| `DSP_RETRIES`        | no       | `20`                          | Retries when DSP answers 429 Too Many Requests.                   |
| `MAX_INGEST_BYTES`   | no       | no limit                      | Files above this size are not ingested.                           |
| `SYNC_WORKERS`       | no       | `4`                           | Items that sync at the same time. `1` syncs one item at a time.   |

## Usage

```bash
# Check the payloads and log the planned changes. Write nothing to DSP.
uv run omeka2dsp sync --dry-run --ids-file test_ids.txt

# Sync all items of the item set.
uv run omeka2dsp sync

# Sync two items.
uv run omeka2dsp sync --id abb13025 --id abb14375

# Sync 2 random items.
uv run omeka2dsp sync --sample 2
```

To upload clean data, make a snapshot with [sgb-data-validator](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator) first (`sgb download`, `sgb transform`).
Then give the snapshot directory to `sync`:

```bash
uv run omeka2dsp sync --snapshot SNAPSHOT_DIR --ids-file test_ids.txt --dry-run
uv run omeka2dsp sync --snapshot SNAPSHOT_DIR --ids-file test_ids.txt
```

After the upload, do a second dry run.
It may log `would create` only for the records that had errors in the upload.
All other records must log "exists already, no changes".

Each `sync` run writes its log to `data_2_dasch.log` and replaces the old log.
Give `--log-file FILE` to keep the log of each run.

| Option            | Effect                                                             |
| ----------------- | ------------------------------------------------------------------ |
| `--snapshot DIR`  | Read items and media from a snapshot directory.                    |
| `--id ID`         | Select the item with this `dcterms:identifier`. You can repeat it. |
| `--ids-file FILE` | Select the identifiers in a file, one on each line.                |
| `--sample N`      | Select N random items.                                             |
| `--dry-run`       | Check the payloads and log the changes. Write nothing to DSP.      |
| `--recreate ID`   | Erase a media record in the wrong class and create it again.       |
| `--log-file FILE` | Write the log to this file. The default is `data_2_dasch.log`.     |

`omeka2dsp add-text-class` prints the request that adds the `Text` class to the DSP ontology.
Add `--apply` to send the request. This needs a DSP user with project-admin rights.

## Checks

```bash
uv run --locked --extra dev pytest test/
uv run --locked --extra dev ruff check src test
uv run --locked --extra dev ruff format --check src test
uv run --locked --extra dev ty check src test
```

CI runs the same four checks.

## Support and contributions

Use [GitHub Issues](https://github.com/Stadt-Geschichte-Basel/omeka2dsp/issues) for bugs, bad data, and requests.
Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull request.
Report security problems as [SECURITY.md](SECURITY.md) tells you.

## Authors

- **Stadt.Geschichte.Basel**: [Stadt-Geschichte-Basel](https://github.com/Stadt-Geschichte-Basel)
- **Nico Görlich**: initial scripts, [koilebeit](https://github.com/koilebeit)

## License

- Code: GNU Affero General Public License v3.0. See [LICENSE.md](LICENSE.md).
- Data: Creative Commons Attribution 4.0 International. See [LICENSE-CCBY.md](LICENSE-CCBY.md).
