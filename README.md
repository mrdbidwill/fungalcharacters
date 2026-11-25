# fungalcharacters

A universal, free, publicly maintained source of fungal character names, value types, value options and descriptions.

Main site (planned): fungalcharacters.org

## Free to use

Everything here is free to use in any way.

- **Character data** (names, value types, value options, descriptions, comments): [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), public domain dedication. No permission or attribution required.
  Please cite as: Fungal Characters, release 1.0.0, https://fungalcharacters.org/
- **Code**: MIT License. See [LICENSE](LICENSE).

## Project decisions

See [docs/DECISIONS.md](docs/DECISIONS.md), the authority for this project.

## Character data

The data is the `fungal_characters` release 1.0.0 (747 characters, 590 value options), loaded exactly as released from [data/releases/1.0.0/](data/releases/1.0.0/). Every character has a permanent code (FCC#####) and every value option one too (FCV#####); codes are never changed or reused. Permanent address: https://fungalcharacters.org/id/FCC00019

## Translating

Volunteers translate the site and the character data: see [docs/TRANSLATING.md](docs/TRANSLATING.md).

## Downloads

The release files are in [data/releases/](data/releases/) and on the site's Downloads page.

## Status

Local only so far. Accounts (sign up, log in); adding and editing characters, value options, value types and sources; duplicate and similar-name checks; ownership rules; public edit history and recent changes; English / scientific name toggle.

## Running locally

- `docker compose up -d`, then open http://localhost:8000/ (home) or http://localhost:8000/characters/
- On an empty database, `migrate` (run automatically on start) loads the release file.
- Tests: `docker compose exec web python manage.py test characters`
