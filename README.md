# fungalcharacters

A universal, free, publicly maintained source of fungal character names, values, value options and descriptions.

Main site (planned): fungalcharacters.org

## Free to use

Everything here is free to use in any way.

- **Character data** (names, values, value options, descriptions, comments): [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), public domain dedication. No permission or attribution required.
- **Code**: MIT License. See [LICENSE](LICENSE).

## Project decisions

See [docs/DECISIONS.md](docs/DECISIONS.md), the authority for this project.

## Status

Local only so far.

- Stage 1: Django + PostgreSQL in Docker, data model, import from the old MRDBID database, list and detail pages.
- Stage 2: accounts (sign up, log in), adding and editing characters, value options, value types and sources; duplicate and similar-name checks; ownership rules; public edit history and recent changes.

## Running locally

- `docker compose up -d`, then open http://localhost:8000/
- Import from MRDBID: `scripts/export_mrdbid.sh` (on the Mac; reads MySQL through the client only, writes `import_data/`), then `docker compose exec web python manage.py import_mrdbid` (add `--replace` to re-import).
- Tests: `docker compose exec web python manage.py test characters`
