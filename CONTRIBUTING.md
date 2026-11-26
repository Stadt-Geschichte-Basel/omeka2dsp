# Contributing

Open an issue before you start a large change.
Follow the [code of conduct](CODE_OF_CONDUCT.md).

## Setup

Follow the setup in the [README](README.md#setup).
Run `pnpm install` once. It installs the pre-commit hook that runs Prettier.

## Checks

Run these checks before you open a pull request.
CI runs the same commands.

```bash
uv run --locked --extra dev pytest test/
uv run --locked --extra dev ruff check src test
uv run --locked --extra dev ruff format --check src test
uv run --locked --extra dev ty check src test
pnpm run check
```

## Pull requests

1. Make a branch with the name `work/<task>` from `main`.
2. Write the commit messages as [Conventional Commits](https://www.conventionalcommits.org/), for example `fix: skip empty values`.
3. Update the README and `docs/` when you change a setting, an option, or the behaviour.
4. Update the golden files in `test/golden/` only for an intended change. See [Architecture](docs/architecture/index.qmd#tests).
5. Open the pull request against `main` of `Stadt-Geschichte-Basel/omeka2dsp`.
6. Merge with a squash merge after the checks pass.
