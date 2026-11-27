# Changelog

## 1.1.0 — 2026-11-27
Core character order: five characters listed twice now keep the lower number. Value types have readable display names.
- Characters: 0 added, 0 with a changed name or definition, 0 removed (codes stay retired, never reused).
- Value options: 0 added, 0 removed.
- Downloads now say "value options" and "value type": columns value_options, value_option_code, value_option, value_type; Excel sheet "Value options"; file csv/value_options_flat.csv (was values_flat.csv).
- Value type keys renamed: drop-down → drop_down.
- Value types now have display names (labels table, type DisplayOption; new column value_type_label next to value_type). The keys in value_type stay permanent.

## 1.0.0 — 2026-11-25
First release.
- Rebuilt from XDE's character list, the Mushroom Observer list 1417 and the old mrdbid_development data; every old character accounted for (one test record dropped).
- Permanent codes for characters (FCC) and values (FCV).
- Labels table for names, scientific names and definitions by language.
- Fungus-type "applies to" tags.
- Spores: average, minimum and maximum length and width, measurement method and number measured. Other microscopic structures: length and width as µm ranges.
- Downloads: Excel, CSV, JSON, SQL (MySQL 8 and PostgreSQL 16/17), SKOS, SDD.
- Checked item by item against XDE's Mushroom Observer list 1417: added Aroma When Dried, Pileipellis End Hyphae Form, Cap Setae Form, Baeocystin(1-); added values for short-gill arrangement, colony shape, colony surface, colony opacity and DNA regions; restored the full name (7-Isopropenyl-4-Methylazulen-1-yl)methyl Stearate; noted that XDE uses Cyanescin for Baeocystin.
- License CC0 1.0 (public domain), with a request to cite; permanent web addresses https://fungalcharacters.org/id/<code>.
