# fungalcharacters — working rules for Claude Code

[docs/DECISIONS.md](docs/DECISIONS.md) is the authority for this project. Read it first. Record new decisions there, dated inline.

- Never give Will Terminal commands to type. Claude Code runs them.
- Be concise.
- Number any steps Will must do.
- Commit with clear messages and push after each completed piece of work.
- Mark every new piece of page text for translation and refresh the translation files (docs/TRANSLATING.md, "For maintainers").
- When a decision is final, apply it everywhere it affects in the same piece of work (code, data, release files, build scripts, docs, DECISIONS.md). Do not leave follow-ups for later; ask only about things the decision does not settle (Will, 2026-11-25).

## Character data (2026-11-25)
- The character data is the `fungal_characters` release 1.0.0, in PostgreSQL. Release files: `~/Desktop/XDE_conversion/fungal_characters/release_v1.0.0/`; the PostgreSQL file is in the repository at `data/releases/1.0.0/fungal_characters_v1.0.0_postgresql.sql`, which migration `characters/0001_initial` loads into an empty database.
- The release tables (`mr_characters`, `lookup_items`, `labels`, …) are used exactly as released; Django models for them are `managed = False`. Never alter their structure. Website-only data goes in separate tables.
- Permanent codes: FCC##### (characters) and FCV##### (value options) are never reused or changed. New items get new codes from `CodeCounter`.
- License: data CC0 1.0, with a request to cite "Fungal Characters, release <version>, https://fungalcharacters.org/". Code: MIT.
- The old character system (stage-1 import from MRDBID: old tables, models, import tools, `mrdbid-import` account) was fully removed on 2026-11-25. Backup in `~/Developer/fungalcharacters_backups/`.

