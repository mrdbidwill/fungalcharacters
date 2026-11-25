# fungalcharacters — Decisions

This project's own decision record. It stands apart from `shared_reference/DECISIONS.md` and `WORKSPACE.md`, which do not govern this project. Old projects and files are used only as general guides, never as structure to copy.

Started 2026-11-24. Newest changes are dated inline.

## Purpose
A universal, free, publicly maintained source of fungal character names, value types (e.g. number in mm, text, color, or a list of value options), value options and descriptions. Values recorded for specific mushrooms are out of scope (2026-11-24).

## Replaces
Mushroom Character Vocabulary and Revive MRDBID. Those two projects are removed when Will is ready. All other projects are unaffected.

## Scope
- Characters only: names, value types (e.g. number in mm, text, color, or a list of value options), value options (used as radio buttons or select menus), descriptions, comments. Values recorded for specific mushrooms are out of scope.
- Terms (2026-11-24): a *value* is what one mushroom has for a character (e.g. stem_width = 3 mm, or Abundance = Low); once set, it is a number or text entered, or one of the character's value options. A *value type* is the kind of value a character takes (stored as the character's display option). *Value options* are a character's allowed choices (table `lookup_items`). Release 1.0.0 calls value options "values" (codes FCV#####); from the next release, downloads say "value options" and "value type" too (columns, Excel sheet, `value_options_flat.csv`), matching the site (2026-11-25).
- Example (Will, 2026-11-25): the character "Cap Texture" has a list of value options (Smooth, …) stored in the lookup table (`lookup_items`); a specific mushroom's *value* for it is one chosen value option, recorded by its id/code. A character like "Cap Width" has no options: its value is a measurement (a number in mm). "Characters" means characters in general; a *character name* refers to a specific one.
- Not included: user mushrooms, specimens, genera/species (no MBList), images (deferred).
- Colors appear only as characters ("cap color", "stem color", "spore color"). A fuller color design is a separate later discussion.
- Every term can be shown in English or in scientific/Latin form, switched by a site-wide toggle.
- Other languages (2026-11-25): plan in docs/I18N_PLAN.md. Groundwork done (language system on, page language and text direction declared, direction-neutral styles, accented-Latin font). Website words are translated with .po files; character data translations live in the `labels` table, written by users on the site. Still to decide: first languages, who translates, language prefixes in addresses.
- A "Thanks" page (2026-11-25): first draft from Will is on the site; Will edits it later. Facts checked: Gastón Guzmán 1932–2016; Flora Agaricina Neerlandica vol. 1 (1988, eds Bas, Kuyper, Noordeloos & Vellinga) with Vellinga's glossary section; nolo_mode's iNaturalist guide "Intro To Identifying Fungi". Not checkable online: nolo_mode's permission (Nov 2026), myceliome.com, the 2019 Mushroom Observer date.
- "Where people disagree" wording (2026-11-25) describes what the site does now: each item shows its source, and every change is kept in the public history. Side-by-side competing statements are not built.
- Home page (2026-11-25): says what the site is for, how to view the data here, how to download it, and that registered users can add and edit; plus Will's "Where people disagree" and "No advice about consumption" texts. The character list moved to /characters/ (menu: Characters).

## Users and editing
- Sign-up open to anyone. Everything public.
- Accounts (2026-11-25, django-allauth): sign-up needs an email address, confirmed by a link before the first sign-in; sign in with username or email; password reset, email changes and security notices by email; sign-ups are rate-limited (no hidden anti-bot field: it would trap screen-reader users). Two-factor sign-in (authenticator app plus one-time recovery codes) is available to everyone and required for the admin, including on the admin pages. Clicking your name in the menu opens your account page: email addresses, password, two-factor sign-in, signed-in devices, and everything you added.
- Any logged-in user can add characters, value types and value options, and add value options to characters others created. A comment explaining the reasoning can accompany each create or edit.
- Users edit only their own work. Once others have added to an item, its creator can no longer delete it.
- All items listed equally, with the creator's username shown.
- No duplicates, including near-matches (case, spacing, punctuation, spelling variants); similar names are shown before saving.
- Full public edit history: who changed what, and when.
- No censorship of character data. The community decides which characters survive by using them.

## Admin
- Will is the only admin. Django's "Groups" (permission bundles for several users) are not used and are hidden from the admin pages (2026-11-25).
- Admin acts only on inappropriate material or behavior: hide or delete it, block users.
- Items from a data release (2026-11-25, replaces the 2026-11-24 `mrdbid-import` rule): credited to the release, no user owner. Only Will, as admin, edits or deletes them.
- "Needs review" button, usable by anyone (logged in or not), adds an entry to a list in the admin section. No email. A hidden per-visitor rate limit stops automated flooding.
- Parts, observation methods, fungus types and source types (2026-11-25): admin only. Users pick from them; only the admin adds or changes them.
- Forgotten passwords (2026-11-25): reset by email link (replaces the admin-made one-time links).

## Data access and licensing
- Permanent codes (2026-11-25): FCC##### for characters, FCV##### for value options, from release 1.0.0. Never changed or reused; new items get the next number. Permanent web address: https://fungalcharacters.org/id/<code>. A deleted item's address says the code is retired.
- Downloads in CSV and JSON; open read-only API; dated releases in the GitHub repository.
- Downloads page (2026-11-25): serves the files of the latest release from `data/releases/<version>/` in the repository (Excel, CSV, JSON, SQL for MySQL and PostgreSQL, SKOS, SDD, README, CHANGELOG). The site may hold newer edits than the latest release. The read-only API is not built yet.
- SDD (TDWG Structured Descriptive Data) export after the core site works.
- Data: CC0. Code: MIT. Site and repository state plainly that everything is free to use in any way.
- CC0 confirmed (2026-11-25) over CC BY 4.0, with a request (not a requirement) to cite: "Fungal Characters, release <version>, https://fungalcharacters.org/".
- Release 1.0.0 files relabelled CC0 (2026-11-25): license wording only, data unchanged; the release build scripts now write CC0. Backups in `~/Developer/fungalcharacters_backups/`.

## Character data
- Source of the data (2026-11-25): the `fungal_characters` release, starting with 1.0.0 (747 characters, 590 value options, 2681 labels). Release files on the Mac: `~/Desktop/XDE_conversion/fungal_characters/release_v1.0.0/`; the PostgreSQL file is also in the repository at `data/releases/1.0.0/`. Built from XDE's character list, Mushroom Observer list 1417 and the old mrdbid_development data.
- Where data is edited (2026-11-25): on the website. Release 1.0.0 is the starting point; the community edits on the site; future releases are produced from the site.
- Release tables are used exactly as released (`mr_characters`, `lookup_items`, `labels`, `character_fungus_types`, `releases`, …). Django never creates or alters them; a reset or deploy loads them from the release file. Website-only data (creator, hidden flag, edit history, code counters) lives in separate tables.
- Core order fix (Will, 2026-11-25): five characters listed twice in the Boletes core order keep the lower number (Cap Surface Texture #11, Gill Breadth #17, Gill Attachment #16, Stem Length #36, Stem Surface Texture #39); the higher entries were removed on the site and the removals are in the public history. Release 1.0.0 files are unchanged; the next release, produced from the site, will carry the fix.
- Going live (2026-11-25): because edits are made on the site, the live site starts from a copy of the local database, not a fresh load of release 1.0.0.
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

## Look and accessibility (2026-11-25)
- Readability and accessibility come first: WCAG 2.2, with AAA contrast (at least 7:1) for all text in light and dark modes; links always underlined; visible amber focus ring; skip-to-content link; large click targets; follows the reader's light/dark, contrast, motion and text-size settings.
- Typeface: Atkinson Hyperlegible (Braille Institute, for low-vision readers; SIL Open Font License), served from the site itself.
- Colours: forest green (#1F4D2E) header and buttons, warm off-white background, near-black text.
- Logo and browser icon: a plain mushroom outline (domed cap, short stem); the icon is cream on a dark-green rounded square.

## Domains
- fungalcharacters.org is the main address; fungalcharacters.com forwards to it.
- mrdbid.com forwards to fungalcharacters.org until mrdbid.com expires.

## Open
- Email (2026-11-25): development uses Mailpit (a local inbox at http://localhost:8025/; nothing is delivered). Production sending service and sending address not yet chosen; the site reads its SMTP settings from the server's environment, so any provider works.
- Deployment: own nginx entry, certificate, containers, database and port (gulfcoastfungi uses 8010); own deploy user or extended rights (current `gcf` user is limited to gulfcoastfungi); mrdbid.com's nginx entry changed to redirect.
- Old shared WORKSPACE.md and DECISIONS.md stay in place: they still govern other projects (gulfcoastfungi, Website Admin). fungalcharacters ignores them. Cleanup is a separate decision for those projects.
