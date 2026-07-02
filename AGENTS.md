# Agent instructions

## Repository identity — read before opening PRs

This repository is **Stadt-Geschichte-Basel/omeka2dsp** and it is **independent**.
It was originally forked from `koilebeit/omeka2dsp`, but the two codebases have
diverged too much to exchange changes.

- **Never open PRs against `koilebeit/omeka2dsp`** (the `upstream` git remote).
  Do not sync, rebase onto, or merge from it either.
- All PRs target `main` on `origin` (Stadt-Geschichte-Basel/omeka2dsp).
- If a `gh` command resolves the base repo to `koilebeit/omeka2dsp`, that is a
  bug caused by the leftover `upstream` remote — pass
  `--repo Stadt-Geschichte-Basel/omeka2dsp` explicitly.
