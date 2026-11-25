# Fungal Characters — release 1.0.0 (2026-11-25)

A reference list of characters (observable features) used to describe and identify fungi: 747 characters and 590 pick-list values.

## Files
| File | For |
|---|---|
| fungal_characters_v1.0.0.xlsx | Anyone: browse in Excel or Numbers |
| csv/characters_flat.csv, csv/values_flat.csv | Anyone: one row per character / per value |
| csv/*.csv (other files) | One file per database table |
| fungal_characters_v1.0.0.json | Programmers |
| fungal_characters_v1.0.0.sql | Websites and databases (MySQL 8) |
| fungal_characters_v1.0.0_postgresql.sql | Websites and databases (PostgreSQL 16/17) |
| fungal_characters_v1.0.0_skos.ttl | Vocabulary tools (W3C SKOS, Turtle) |
| fungal_characters_v1.0.0_sdd.xml | Identification-key tools (TDWG SDD 1.1; validated against the official schema) |

## Identifiers
Each character has a permanent code (FCC#####) and each value a permanent code (FCV#####). Codes are never reused or changed. Each code's permanent web address is https://fungalcharacters.org/id/<code>, e.g. https://fungalcharacters.org/id/FCC00019 (Cap Width). Use them when linking your data to this list.

## Names and languages
Every character has an English name and a scientific name (e.g. Cap Width / Pileus Width), plus a definition where available. These live in the labels table by language, so translations can be added without changing anything else.

## Fungus types
"Applies to" tags show which fungus types a character is specific to. No tag means it applies to all fungi.

## Sources
- XDE (nolo_mode), "Simple & Advanced Characters With Taxonomic Value For Stipitate-Lamellate Mushrooms", iNaturalist. All 213 character lines of that list are included (364 characters trace to it).
- XDE's Mushroom Observer species list 1417.
- The earlier mrdbid_development character database (Kit Scates' guides and other books listed in source_data).

## Notes
- Values or units marked "proposal" in comments were added where the sources gave none.
- Compound names marked "UNVERIFIED" in comments could not be confirmed in the literature; experts are invited to resolve them.

## License and citation
CC0 1.0 (public domain dedication, https://creativecommons.org/publicdomain/zero/1.0/). Free to use in any way, including commercially, with no permission or credit required.
Please cite as: Fungal Characters, release 1.0.0, https://fungalcharacters.org/
