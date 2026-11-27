# Making a data release

A release is a dated snapshot of the live data at fungalcharacters.org, in every download format. Releases are made
when Will says so (they are public). Version numbers: 1.1.0 for new or changed data, 2.0.0 only if the table
structure ever changes.

## What a release contains
`data/releases/<version>/` in the repository, served on the Downloads page once recorded:
Excel, CSV (flat views plus one file per table), JSON, SQL for PostgreSQL 16/17 and for MySQL 8, SKOS (Turtle),
SDD 1.1 (XML), README.md and CHANGELOG.md (with what changed since the previous release, by permanent code).

- Made by `python manage.py make_release` (code: `characters/release.py`), ported from the 1.0.0 build scripts.
- The SQL files keep the exact table definitions, comments and indexes of the previous release (copied word for
  word); only data rows are new. Checked for the first build (2026-11-26): both files load into empty PostgreSQL 17
  and MySQL 8 databases; structure identical to 1.0.0; every table equal to the site's data.
- Hidden items are left out; references to them are emptied.
- Downloads use the site's terms: value options, value type (from the first release after 1.0.0; the changelog says so).

## Steps (Claude runs them after Will's go)
1. `deploy/make_release.sh <version> "<one-line notes>"` — builds from the live database inside the running app and
   copies the files into `data/releases/<version>/` on the Mac. Nothing in the database changes.
2. Check: tests pass; spot-check README, CHANGELOG and counts.
3. Commit and push; `deploy/deploy.sh`.
4. Record it (footer and Downloads page switch to the new release): the `--record-only` command the script prints.
5. Dated GitHub release with the files attached (docs/DECISIONS.md: dated releases in the GitHub repository).
   Tag `data-v<version>` (data releases, not code versions), title "Fungal Characters data release <version> (<date>)",
   notes from the CHANGELOG, files: xlsx, json, both sql, ttl, sdd.xml, README.md and the csv folder as a zip:
   `gh release create data-v<version> --repo mrdbidwill/fungalcharacters --target main --title "…" --notes-file notes.md <files>`.
   First one: data-v1.0.0, published 2026-11-26 (https://github.com/mrdbidwill/fungalcharacters/releases/tag/data-v1.0.0).
6. Zenodo (switched on 2026-11-27) archives the GitHub release automatically and gives it a DOI, using `.zenodo.json`
   (creators: Johnston, Will and Fungal Characters contributors; contributor: nolo_mode (XDE); CC0 for the data,
   MIT for code). Find the DOI (Zenodo › Upload or https://zenodo.org/search?q=fungalcharacters), add it to
   `RELEASE_DOIS` in config/settings.py, deploy, and check the Downloads page shows it.
7. Update "latest" mentions (README.md).

## Why the release file in migration 0001 stays 1.0.0
Migration `characters/0001_initial` loads `data/releases/1.0.0/` into an empty database (a reset or a fresh server).
The live site is never reloaded from a release: its database is the source, and releases are made from it.
