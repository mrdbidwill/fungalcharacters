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
- Other languages (Will, 2026-11-25): Spanish, Thai, Portuguese (Brazil) and French first; volunteers translate, with a supportive framework (docs/TRANSLATING.md, docs/I18N_PLAN.md). Built: all page text marked for translation, .po files per language, a Languages page (choose language, progress, preview, "Translate characters"), and on-site translation of character names, definitions and value options (stored in `labels`, credited, in the history; users edit their own, the admin any). A language joins the language menu and browser matching when Will says it is ready (PUBLISHED_LANGUAGES). No language prefix in addresses. Website words: Hosted Weblate recommended, waiting for Will's sign-up.
- Name switch wording (2026-11-25): "Common · Scientific" instead of "English · Scientific", because common names are shown in the reader's language.
- Hosted page (2026-11-25): Brian Hunt's Lumen Granuli Praecisi (v1.0) is kept at /documents/lumen-granuli-praecisi/, the same path it had on mrdbid.com (Will 2026-11-11: keep it working), as a byte-for-byte copy of the MRDBID app's hosted files, with the site bar and the disclaimer added top and bottom. mrdbid.com/documents/… forwards to the same path here. The Thanks page has a card linking to it (Will).
- A "Thanks" page (2026-11-25): first draft from Will is on the site; Will edits it later. Facts checked: Gastón Guzmán 1932–2016; Flora Agaricina Neerlandica vol. 1 (1988, eds Bas, Kuyper, Noordeloos & Vellinga) with Vellinga's glossary section; nolo_mode's iNaturalist guide "Intro To Identifying Fungi". Not checkable online: nolo_mode's permission (Nov 2026), myceliome.com, the 2019 Mushroom Observer date.
- "Where people disagree" wording (2026-11-25) describes what the site does now: each item shows its source, and every change is kept in the public history. Side-by-side competing statements are not built.
- Disclaimer (2026-11-25, Website Administrator; rule in Claude_AI/shared_reference/disclaimer/): "No advice about consumption." at the top and bottom of every page in the shared style, and the short note beside characters about chemistry or toxicity (chemical-test methods, "Toxic") and sources whose titles are about eating or medicinal use.
- Home page: its own "No advice about consumption" section removed (Will, 2026-11-26; replaces the 2026-11-25 choice to keep it): the same notice is at the top and bottom of every page. "Where people disagree" ends: "Mention on the Thanks page does not mean anyone named there endorses any value on the site." (Will, 2026-11-26).
- Characters list (Will, 2026-11-26): 50 per page, with a short note under the heading that the list is alphabetical (numbers first) and meant to include everything.
- Home page (2026-11-25): says what the site is for, how to view the data here, how to download it, and that registered users can add and edit; plus Will's "Where people disagree" and "No advice about consumption" texts. The character list moved to /characters/ (menu: Characters).

## Users and editing
- Sign-up open to anyone. Everything public.
- Email (2026-11-25): development uses Mailpit (a local inbox at http://localhost:8025/; nothing is delivered); the live site sends through Resend from no-reply@mail.fungalcharacters.org.
- Accounts (2026-11-25, django-allauth): sign-up needs an email address, confirmed by a link before the first sign-in; sign in with username or email; password reset, email changes and security notices by email; sign-ups are rate-limited. Anti-bot (Will, 2026-11-26, after a bot signed up with a stranger's email address): a honeypot field hidden with display:none (invisible to screen readers and keyboards too; bots that fill it get a fake "check your email" page, no account, no email); allauth limits sign-up to 5 an hour per address and password-reset requests to 5 an hour per address and 3 an hour per email; nginx also limits POSTs to the sign-up and reset pages (6 a minute per address, burst 3). robots.txt (Will, 2026-11-26) asks crawlers to skip sign-in, account, edit and report pages, the names switch and the raw API; everything people read stays open. Cloudflare Turnstile is the next step if bots still get through (note: WORKSPACE.md said "no Cloudflare anywhere"; Will to decide). The one bot account (unverified, never signed in) was deleted. Two-factor sign-in (authenticator app plus one-time recovery codes) is available to everyone and required for the admin, including on the admin pages. Clicking your name in the menu opens your account page: email addresses, password, two-factor sign-in, signed-in devices, and everything you added.
- Any logged-in user can add characters, value types and value options, and add value options to characters others created. A comment explaining the reasoning can accompany each create or edit.
- Users edit only their own work. Once others have added to an item, its creator can no longer delete it.
- All items listed equally, with the creator's username shown.
- No duplicates, including near-matches (case, spacing, punctuation, spelling variants); similar names are shown before saving.
- Full public edit history: who changed what, and when.
- No censorship of character data. The community decides which characters survive by using them.

## Contributions and privacy (2026-11-25)
- Contribution terms: everything users add (characters, value types, value options, sources, translations, change reasons) is public and dedicated to CC0 1.0; users confirm they have the right to share it and do not paste others' text unless its license allows. Agreed with a required checkbox at sign-up; accounts that existed before are asked once before they next add anything. Each agreement is recorded (Consent: user, version, date; current version 2026-11-25). A new version of the terms asks everyone again.
- Privacy page /privacy/ ("Contributions and privacy"), linked from the footer, the account page and every save form: what is stored, where (Hostinger server in the US; email via Resend, US), web logs 14 days, nightly backups (30 days on the server, plus the Website Administrator's off-server copy), no analytics, ads, tracking or third-party scripts.
- The privacy page was checked against the code by an independent review (2026-11-25); its findings were fixed: the site records visitors' real IP addresses (one trusted proxy, nginx), so rate limits and the signed-in devices list work per visitor; the common/scientific choice is a cookie (no server-side session for anonymous visitors); expired sessions are cleared nightly; the app's own logs are capped (3 × 10 MB); error reports never contain passwords, codes or keys.
- Contact for privacy questions: contact@fungalcharacters.org, forwarded to Will (Will, 2026-11-25); the Website Administrator sets up the forwarding.
- "Delete my account" (account page; password asked again): deletes email addresses, password, two-factor settings and sessions, signs out; contributions stay, credited to "former-contributor-<number>". Not available for the admin account.

## Admin
- Will is the only admin. Django's "Groups" (permission bundles for several users) are not used and are hidden from the admin pages (2026-11-25).
- Admin acts only on inappropriate material or behavior: hide or delete it, block users.
- Items from a data release (2026-11-25, replaces the 2026-11-24 `mrdbid-import` rule): credited to the release, no user owner. Only Will, as admin, edits or deletes them.
- "Needs review" button, usable by anyone (logged in or not), adds an entry to a list in the admin section. No email. A hidden per-visitor rate limit stops automated flooding. Built 2026-11-26: on character, value type and source pages (value options are reported from their character); optional note; the list is in the admin pages (mark resolved), and the admin's account page shows the open count. Limit: 5 reports an hour per visitor (signed in: per account); beyond that reports are dropped with the same thank-you. The visitor's IP is used only hashed, as a one-hour counter. Rate-limit counters (this and allauth's sign-in limits) live in a database cache shared by all server processes.
- Parts, observation methods, fungus types and source types (2026-11-25): admin only. Users pick from them; only the admin adds or changes them.
- Forgotten passwords (2026-11-25): reset by email link (replaces the admin-made one-time links).

## Data access and licensing
- Permanent codes (2026-11-25): FCC##### for characters, FCV##### for value options, from release 1.0.0. Never changed or reused; new items get the next number. Permanent web address: https://fungalcharacters.org/id/<code>. A deleted item's address says the code is retired.
- Downloads in CSV and JSON; open read-only API; dated releases in the GitHub repository.
- GitHub releases (2026-11-26): each data release is also a GitHub release, tag `data-v<version>`, with its files attached; data-v1.0.0 published.
- Read-only API (2026-11-26): /api/v1/ characters (search, filters, paging), one character with value options and translations, value options, releases; JSON, no key, open to any website (CORS), CC0; hidden items never appear; fair-use limit 120 requests a minute per address (429 beyond). Explained at /api/.
- Downloads page (2026-11-25): serves the files of the latest release from `data/releases/<version>/` in the repository (Excel, CSV, JSON, SQL for MySQL and PostgreSQL, SKOS, SDD, README, CHANGELOG). The site may hold newer edits than the latest release. The read-only API is not built yet.
- SDD (TDWG Structured Descriptive Data) export after the core site works.
- Data: CC0. Code: MIT. Site and repository state plainly that everything is free to use in any way.
- CC0 confirmed (2026-11-25) over CC BY 4.0, with a request (not a requirement) to cite: "Fungal Characters, release <version>, https://fungalcharacters.org/".
- Release 1.0.0 files relabelled CC0 (2026-11-25): license wording only, data unchanged; the release build scripts now write CC0. Backups in `~/Developer/fungalcharacters_backups/`.

## Character data
- Source of the data (2026-11-25): the `fungal_characters` release, starting with 1.0.0 (747 characters, 590 value options, 2681 labels). Release files on the Mac: `~/Desktop/XDE_conversion/fungal_characters/release_v1.0.0/`; the PostgreSQL file is also in the repository at `data/releases/1.0.0/`. Built from XDE's character list, Mushroom Observer list 1417 and the old mrdbid_development data.
- Releases from the site (2026-11-26): `make_release` builds a dated release from the live data in every download format; the SQL files keep the previous release's exact table definitions; hidden items are left out; the changelog lists changes by permanent code. Made when Will says so (docs/RELEASING.md).
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
- mrdbid.com forwards to fungalcharacters.org until mrdbid.com expires. Live since 2026-11-25 15:28 CT (302 for the first week; the Website Administrator switches it to 301 and raises HSTS on 2026-12-02). Start: now (Will, 2026-11-25); www and new.mrdbid.com too, all to the home page except /documents/… (same path here, for Brian Hunt's page); dna.mrdbid.com is not included. The Website Administrator makes the nginx change (request: Claude_AI/Website_Admin/FC_REQUEST_MRDBID_REDIRECT.md).

## Open
- Live (2026-11-25): https://fungalcharacters.org/ (www and .com redirect to it). Website Administrator did the server setup, nginx, DNS and certificate; this project deploys the app with deploy/deploy.sh (docs/DEPLOY.md). App in Docker, Compose project `fungalcharacters`, gunicorn on 127.0.0.1:8030 (8010 gulfcoastfungi, 8020 mrdbid.com). The live database started as a copy of the local one. Email sends through Resend (mail.fungalcharacters.org verified). Nightly private backups on the server (03:15). Admin account `will` (willfh54@protonmail.com) signs in with two-factor; site error reports go to that address. mrdbid.com's redirect: see Domains.
- Old shared WORKSPACE.md and DECISIONS.md stay in place: they still govern other projects (gulfcoastfungi, Website Admin). fungalcharacters ignores them, except WORKSPACE.md §5a (Will, 2026-11-25): server, DNS, certificates and GitHub settings belong to the Website Administrator; any change to them beyond deploying the app gets one line in Website_Admin/ADMIN.md under Incoming. Cleanup is a separate decision for those projects.
- Handled by the Website Administrator (Will, 2026-11-25): copies of the nightly database backups (its existing nightly pull; not copied to Will's Mac by this project), the 2026-12-02 items (302 → 301, HSTS one year), MRDBID's sudo rule, gulfcoastfungi.com's link to Brian Hunt's page, and Weblate (set up when this project is ready to add languages). The Resend SMTP key was replaced 2026-11-25 ("fungalcharacters.org SMTP 2026-11-25"; the earlier key deleted); sending checked afterwards.
