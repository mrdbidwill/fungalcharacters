# fungalcharacters — Decisions

This project's own decision record. It stands apart from `shared_reference/DECISIONS.md` and `WORKSPACE.md`, which do not govern this project. Old projects and files are used only as general guides, never as structure to copy.

Started 2026-11-24. Newest changes are dated inline.

## Purpose
A universal, free, publicly maintained source of fungal character names, value types (e.g. number in mm, text, color, or a list of value options), value options and descriptions. Values recorded for specific mushrooms are out of scope (2026-11-24).

## Replaces
Mushroom Character Vocabulary and Revive MRDBID. Those two projects are removed when Will is ready. All other projects are unaffected.

## Scope
- Characters only: names, value types (e.g. number in mm, text, color, or a list of value options), value options (used as radio buttons or select menus), descriptions, comments. Values recorded for specific mushrooms are out of scope.
- Terms (2026-11-24): a *value* is what one mushroom has for a character (e.g. stem_width = 3 mm, or Abundance = Low); once set, it is a number or text entered, or one of the character's value options. A *value type* is the kind of value a character takes (stored as the character's display option). *Value options* are a character's allowed choices (table `lookup_items`). The data release calls value options "values" (codes FCV#####); the site says "value options" (2026-11-25).
- Not included: user mushrooms, specimens, genera/species (no MBList), images (deferred).
- Colors appear only as characters ("cap color", "stem color", "spore color"). A fuller color design is a separate later discussion.
- Every term can be shown in English or in scientific/Latin form, switched by a site-wide toggle.
- A "Thanks" page, content supplied by Will later.

## Users and editing
- Sign-up open to anyone. Everything public.
- Any logged-in user can add characters, value types and value options, and add value options to characters others created. A comment explaining the reasoning can accompany each create or edit.
- Users edit only their own work. Once others have added to an item, its creator can no longer delete it.
- All items listed equally, with the creator's username shown.
- No duplicates, including near-matches (case, spacing, punctuation, spelling variants); similar names are shown before saving.
- Full public edit history: who changed what, and when.
- No censorship of character data. The community decides which characters survive by using them.

## Admin
- Will is the only admin.
- Admin acts only on inappropriate material or behavior: hide or delete it, block users.
- Items from a data release (2026-11-25, replaces the 2026-11-24 `mrdbid-import` rule): credited to the release, no user owner. Only Will, as admin, edits or deletes them.
- "Needs review" button, usable by anyone (logged in or not), adds an entry to a list in the admin section. No email. A hidden per-visitor rate limit stops automated flooding.
- Parts, observation methods, fungus types and source types (2026-11-25): admin only. Users pick from them; only the admin adds or changes them.
- Forgotten passwords (2026-11-25): until email is added, the admin makes a one-time "set password" link on request.

## Data access and licensing
- Permanent codes (2026-11-25): FCC##### for characters, FCV##### for value options, from release 1.0.0. Never changed or reused; new items get the next number. Permanent web address: https://fungalcharacters.org/id/<code>. A deleted item's address says the code is retired.
- Downloads in CSV and JSON; open read-only API; dated releases in the GitHub repository.
- SDD (TDWG Structured Descriptive Data) export after the core site works.
- Data: CC0. Code: MIT. Site and repository state plainly that everything is free to use in any way.
- CC0 confirmed (2026-11-25) over CC BY 4.0, with a request (not a requirement) to cite: "Fungal Characters, release <version>, https://fungalcharacters.org/".

## Character data
- Source of the data (2026-11-25): the `fungal_characters` release, starting with 1.0.0 (747 characters, 590 value options, 2681 labels). Release files on the Mac: `~/Desktop/XDE_conversion/fungal_characters/release_v1.0.0/`; the PostgreSQL file is also in the repository at `data/releases/1.0.0/`. Built from XDE's character list, Mushroom Observer list 1417 and the old mrdbid_development data.
- Where data is edited (2026-11-25): on the website. Release 1.0.0 is the starting point; the community edits on the site; future releases are produced from the site.
- Release tables are used exactly as released (`mr_characters`, `lookup_items`, `labels`, `character_fungus_types`, `releases`, …). Django never creates or alters them; a reset or deploy loads them from the release file. Website-only data (creator, hidden flag, edit history, code counters) lives in separate tables.
- Names, scientific names and definitions live in `labels` by language; the English / scientific toggle uses them.
- Provenance: every character, value type and value option added on the site records its creator (user account, automatic) and optionally a cited published source. Published sources are a shared list anyone can cite or add to.
- Old character system removed (2026-11-25): the stage-1 import from MRDBID (767 characters, MRDBID IDs as permanent IDs, `mrdbid-import` account, import tools) was fully replaced. Backup: `~/Developer/fungalcharacters_backups/`. The MySQL databases `fungal_characters` (reference copy) and `mrdbid_development` are not used by the site and are left unchanged.

## Technology
- Django + PostgreSQL in Docker, on the existing Hostinger VPS alongside gulfcoastfungi.com (same stack, one maintenance path).
- Repository: `mrdbidwill/fungalcharacters` on GitHub, public.
- Development in VS Code with Claude Code. No JetBrains IDEs.
- Code folder on the Mac outside Claude_AI (e.g. `~/Developer/fungalcharacters`), where git runs normally.
- Work location (2026-11-24): planning here until the repository exists; then all work moves to VS Code with Claude Code. This file then moves into the repository and the Claude_AI copy becomes a one-line pointer.
- Git/GitHub: Claude Code commits and pushes; Will only signs in to GitHub once. GitHub Desktop stays available for viewing history.

## Domains
- fungalcharacters.org is the main address; fungalcharacters.com forwards to it.
- mrdbid.com forwards to fungalcharacters.org until mrdbid.com expires.

## Open
- Release 1.0.0 files still say CC BY 4.0 (README, CHANGELOG, header comment of the SQL files). They need regenerating with CC0 wording by the release build scripts (`~/Desktop/XDE_conversion/fungal_characters/build_scripts/`) (2026-11-25).
- Email (2026-11-25): to be added soon, for password resets. Provider and sending address not yet chosen.
- Deployment: own nginx entry, certificate, containers, database and port (gulfcoastfungi uses 8010); own deploy user or extended rights (current `gcf` user is limited to gulfcoastfungi); mrdbid.com's nginx entry changed to redirect.
- Old shared WORKSPACE.md and DECISIONS.md stay in place: they still govern other projects (gulfcoastfungi, Website Admin). fungalcharacters ignores them. Cleanup is a separate decision for those projects.
