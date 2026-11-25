# fungalcharacters — Decisions

This project's own decision record. It stands apart from `shared_reference/DECISIONS.md` and `WORKSPACE.md`, which do not govern this project. Old projects and files are used only as general guides, never as structure to copy.

Started 2026-11-24. Newest changes are dated inline.

## Purpose
A universal, free, publicly maintained source of fungal character names, value types (e.g. number in mm, text, color, or a list of value options), value options and descriptions. Values recorded for specific mushrooms are out of scope (2026-11-24).

## Replaces
Mushroom Character Vocabulary and Revive MRDBID. Those two projects are removed when Will is ready. All other projects are unaffected.

## Scope
- Characters only: names, value types (e.g. number in mm, text, color, or a list of value options), value options (used as radio buttons or select menus), descriptions, comments. Values recorded for specific mushrooms are out of scope.
- Terms (2026-11-24): a *value* is what one mushroom has for a character (e.g. stem_width = 3 mm, or Abundance = Low); once set, it is a number or text entered, or one of the character's value options. A *value type* is the kind of value a character takes (stored as the character's display option). *Value options* are a character's allowed choices (old `lookup_items`).
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
- "Needs review" button, usable by anyone (logged in or not), adds an entry to a list in the admin section. No email. A hidden per-visitor rate limit stops automated flooding.

## Data access and licensing
- Permanent, never-reused ID and web address for every character.
- Downloads in CSV and JSON; open read-only API; dated releases in the GitHub repository.
- SDD (TDWG Structured Descriptive Data) export after the core site works.
- Data: CC0. Code: MIT. Site and repository state plainly that everything is free to use in any way.

## Starting data
- Initial set drawn from sources Will selects, seeded from the old MRDBID database: MySQL 8.0 (Homebrew) on the Mac, `127.0.0.1:3306`, database `mrdbid_development`. Read through MySQL (export to a `.sql` file); never copy its data folder by hand.
- Starting set (2026-11-24): all ~790 characters in old `mr_characters`. Will reviews and edits them once editing works on the new site.
- Imported (2026-11-24, stage 1): `mr_characters` actually holds 767 rows (IDs run to 793; 26 were deleted in MRDBID). All 767 imported with their MRDBID IDs as permanent IDs; new IDs start at 794 so deleted IDs are never reused. Imported records are credited to the account `mrdbid-import` and keep their original created/updated times. Six near-duplicate name pairs came across as they were, for Will's review: 233/784 Substrate, 316/782 Aroma, 5/781 Taste, 73/783 Spore Color, 747/777 margin color, 610/618 α-Amanitin Present.
- Provenance: every character, value type and value option records its creator (user account, automatic) and optionally a cited published source. Published sources are a shared list anyone can cite or add to, seeded from old `source_data` / `source_data_types`.
- Old MRDBID tables used as a guide: mr_characters, parts, source_data, source_data_types, observation_methods, lookup_items, fungus_types, display_options.
- The local MRDBID app (`~/Documents/Development/www/public_html/mrdbid`, http://localhost:3000/) is used only to understand the character flow: create, edit, delete, store.

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
- Deployment: own nginx entry, certificate, containers, database and port (gulfcoastfungi uses 8010); own deploy user or extended rights (current `gcf` user is limited to gulfcoastfungi); mrdbid.com's nginx entry changed to redirect.
- Old shared WORKSPACE.md and DECISIONS.md stay in place: they still govern other projects (gulfcoastfungi, Website Admin). fungalcharacters ignores them. Cleanup is a separate decision for those projects.
