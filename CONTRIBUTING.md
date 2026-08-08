# Contributing to MediaDownloader

Thanks for your interest in contributing! Every kind of help is welcome:
bug reports, feature ideas, translations, docs, and code.

> 中文版开发与维护细节见 [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md)。

## Getting started

1. **Fork** the repo and clone your fork.
2. Create a branch: `git checkout -b feat/your-change`
3. Set up the Python environment:

   ```bash
   cd python && uv sync
   uv run playwright install chromium   # only needed for browser-based downloads
   ```

4. Make your change, then run the tests:

   ```bash
   cd python && uv run pytest            # pure unit tests, no network/browser
   ```

5. Commit and open a pull request against `main`.

## Guidelines

- **Keep it focused.** One PR = one logical change.
- **Version numbers** are managed from a single source: `version.json`.
  Do not bump versions by hand — edit `version.json` and run
  `python3 scripts/sync-versions.py`.
- **Changelog**: update `CHANGELOG.md` for user-visible changes. Bullets are
  tagged with the affected client: `**[全平台]**` / `**[CLI]**` /
  `**[Windows]**` / `**[macOS]**` / `**[iOS]**` / `**[Android]**`.
  `changelog.json` is regenerated at release time — don't edit it by hand.
- **Tests** must stay pure (no network, no browser). Parser fixtures go in
  `python/tests/fixtures/` and must be sanitized.
- **Commit messages**: Chinese is fine (repo convention), describe *what* and
  *why*. Prefix with the scope when relevant (e.g. `feat(cli):`, `fix(windows):`).
- **New JSON files at the repo root** need a `!` exception in `.gitignore`
  (it blocks `*.json` globally).
- **Reproducible builds**: don't commit build artifacts under `dist/`.

## Releasing (maintainers only)

1. Edit `version.json` → `python3 scripts/sync-versions.py` (optionally
   `--policies` to mirror policy `min_version` fields).
2. Update `CHANGELOG.md`, then regenerate:
   `python3 scripts/update-changelog-json.py`.
3. Run `./scripts/release.sh` (bumps policy timestamps, tags, pushes — CI
   builds every platform).

## Code of conduct

Be respectful and constructive. Harassment, trolling, or any form of abuse is
not tolerated. Report issues to the maintainers privately.
