"""Build a dated data release from the site's live tables (docs/RELEASING.md).

Ported from the release 1.0.0 build scripts (~/Desktop/XDE_conversion/fungal_characters/build_scripts/export.py and
emit_pg.py), which read the old MySQL copy. This reads the same tables from the site's PostgreSQL database.

- The SQL files keep the exact structure of the previous release: their table definitions, comments and indexes are
  copied word for word from the previous release's files; only the data rows are written fresh.
- Items the admin has hidden are left out (and references to them are emptied).
- Downloads use the site's terms: "value options" and "value type" (docs/DECISIONS.md, Terms).
"""
import csv
import datetime
import decimal
import json
import re
from pathlib import Path

from django.conf import settings
from django.db import connection

LICENSE = "CC0 1.0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
BASE = "https://fungalcharacters.org/id/"
TABLES = ["parts", "observation_methods", "display_options", "source_data_types", "fungus_types", "source_data",
          "mr_characters", "lookup_items", "core_character_sequences", "labels", "character_fungus_types", "releases"]
RELEASES_DIR = settings.BASE_DIR / "data" / "releases"
SRC56 = "XDE: Simple & Advanced Characters With Taxonomic Value For Stipitate-Lamellate Mushrooms"


def cite(version):
    return f"Please cite as: Fungal Characters, release {version}, https://fungalcharacters.org/"


# ---------- reading ----------

def read_tables():
    data = {}
    with connection.cursor() as cur:
        for t in TABLES:
            cur.execute(f"SELECT * FROM {t} ORDER BY id")
            cols = [c.name for c in cur.description]
            data[t] = [dict(zip(cols, row)) for row in cur.fetchall()]
    for c in data["mr_characters"]:   # jsonb arrives as text through Django's raw cursor
        if isinstance(c["properties"], str):
            c["properties"] = json.loads(c["properties"])
    return data


def drop_hidden(data):
    """Leave out hidden items and empty references to them. Returns counts of what was left out."""
    from .models import ItemMeta
    hidden = {}
    for t in ("MrCharacter", "LookupItem", "SourceData", "DisplayOption"):
        hidden[t] = set(ItemMeta.objects.filter(item_type=t, is_hidden=True).values_list("item_id", flat=True))
    hc, hv, hs, hd = hidden["MrCharacter"], hidden["LookupItem"], hidden["SourceData"], hidden["DisplayOption"]
    hv |= {v["id"] for v in data["lookup_items"] if v["mr_character_id"] in hc}
    data["mr_characters"] = [c for c in data["mr_characters"] if c["id"] not in hc]
    data["lookup_items"] = [v for v in data["lookup_items"] if v["id"] not in hv]
    data["core_character_sequences"] = [r for r in data["core_character_sequences"] if r["mr_character_id"] not in hc]
    data["character_fungus_types"] = [r for r in data["character_fungus_types"] if r["mr_character_id"] not in hc]
    data["labels"] = [l for l in data["labels"] if not (
        (l["labelable_type"] == "MrCharacter" and l["labelable_id"] in hc)
        or (l["labelable_type"] == "LookupItem" and l["labelable_id"] in hv))]
    data["source_data"] = [s for s in data["source_data"] if s["id"] not in hs]
    data["display_options"] = [d for d in data["display_options"] if d["id"] not in hd]
    for row in data["mr_characters"] + data["lookup_items"]:
        if row.get("source_data_id") in hs:
            row["source_data_id"] = None
    for c in data["mr_characters"]:
        if c["display_option_id"] in hd:
            c["display_option_id"] = None
    return {"characters": len(hc), "value_options": len(hv), "sources": len(hs), "value_types": len(hd)}


# ---------- SQL (structure copied from the previous release) ----------

def pg_lit(v, col):
    if v is None:
        return "NULL"
    if col == "needs_review":
        return "true" if v else "false"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, decimal.Decimal)):
        return str(v)
    if isinstance(v, datetime.datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S.%f") + "'"
    if isinstance(v, datetime.date):
        return "'" + v.isoformat() + "'"
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    return "'" + str(v).replace("'", "''") + "'"


def my_lit(v, col):
    if v is None:
        return "NULL"
    if col == "needs_review" or isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, decimal.Decimal)):
        return str(v)
    if isinstance(v, datetime.datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S.%f") + "'"
    if isinstance(v, datetime.date):
        return "'" + v.isoformat() + "'"
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def write_postgresql(data, version, prev_file, out_file):
    lines = prev_file.read_text(encoding="utf-8").split("\n")
    first_insert = next(i for i, l in enumerate(lines) if l.startswith("INSERT INTO "))
    structure = [l for l in lines[2:first_insert] if not l.startswith("DO $$")]   # BEGIN; SET; CREATE TABLE; COMMENT
    indexes = [l for l in lines if l.startswith("CREATE INDEX") or l.startswith("CREATE UNIQUE INDEX")]
    out = [f"-- fungal_characters release {version} — PostgreSQL 16/17 version. License {LICENSE} (public domain), https://fungalcharacters.org/",
           "-- Same tables, columns and data as the MySQL release. Load into an empty database or schema."] + structure
    for t in TABLES:
        rows = data[t]
        if rows:
            cols = list(rows[0].keys())
            for i in range(0, len(rows), 200):
                chunk = rows[i:i + 200]
                out.append(f"INSERT INTO {t} ({', '.join(cols)}) VALUES\n" +
                           ",\n".join("(" + ", ".join(pg_lit(r[c], c) for c in cols) + ")" for r in chunk) + ";")
        out.append(f"DO $$ BEGIN PERFORM setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT max(id) FROM {t}), 1)); END $$;")
    out += indexes + ["COMMIT;"]
    out_file.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_mysql(data, version, prev_file, out_file):
    lines = prev_file.read_text(encoding="utf-8").split("\n")
    first_insert = next(i for i, l in enumerate(lines) if l.startswith("INSERT INTO "))
    structure = lines[2:first_insert]   # CREATE DATABASE, USE, SET NAMES, CREATE TABLE ...
    out = [f"-- fungal_characters release {version} — MySQL 8 version. License {LICENSE} (public domain), https://fungalcharacters.org/",
           f"-- Same table and column layout as release 1.0.0. Generated {datetime.date.today().isoformat()} from fungalcharacters.org."] + structure
    for t in TABLES:
        rows = data[t]
        if not rows:
            continue
        cols = list(rows[0].keys())
        out.append(f"INSERT INTO `{t}` ({', '.join('`' + c + '`' for c in cols)}) VALUES\n" +
                   ",\n".join("(" + ", ".join(my_lit(r[c], c) for c in cols) + ")" for r in rows) + ";")
    out_file.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------- the other formats (ported from export.py) ----------

def build_views(data):
    by = lambda t: {r["id"]: r for r in data[t]}
    parts, meths, disps, fts, srcs = by("parts"), by("observation_methods"), by("display_options"), by("fungus_types"), by("source_data")
    vals, tags = {}, {}
    for v in data["lookup_items"]:
        vals.setdefault(v["mr_character_id"], []).append(v)
    for t in data["character_fungus_types"]:
        tags.setdefault(t["mr_character_id"], []).append(fts[t["fungus_type_id"]]["name"])
    vt_labels = {l["labelable_id"]: l["text"] for l in data["labels"]
                 if l["labelable_type"] == "DisplayOption" and l["label_type"] == "name" and l["language"] == "en"}
    flat = []
    for c in data["mr_characters"]:
        p = c["properties"] or {}
        flat.append({
            "code": c["code"], "name": c["name"], "scientific_name": p.get("name_scientific"),
            "definition": c["description"], "part": (parts.get(c["part_id"]) or {}).get("name"),
            "observation_method": (meths.get(c["observation_method_id"]) or {}).get("name"),
            "value_type": (disps.get(c["display_option_id"]) or {}).get("name"), "unit": p.get("unit"),
            "value_type_label": vt_labels.get(c["display_option_id"]),
            "value_options": " | ".join(v["name"] or "" for v in vals.get(c["id"], [])),
            "applies_to_fungus_types": ", ".join(tags.get(c["id"], [])) or "All",
            "starter_set": "Yes" if p.get("common") else "", "xde_lines": ", ".join(map(str, p.get("xde_lines", []))),
            "source": SRC56 if c["source_data_id"] == 56 else (srcs.get(c["source_data_id"]) or {}).get("title"),
            "comments": c["comments"], "id": c["id"]})
    code_of = {c["id"]: c for c in data["mr_characters"]}
    flat_vals = [{"value_option_code": v["code"], "character_code": code_of[v["mr_character_id"]]["code"],
                  "character": code_of[v["mr_character_id"]]["name"], "value_option": v["name"], "definition": v["description"]}
                 for v in data["lookup_items"]]
    labels = {}
    for l in data["labels"]:
        labels.setdefault((l["labelable_type"], l["labelable_id"]), []).append(
            {"language": l["language"], "type": l["label_type"], "text": l["text"]})
    return {"vals": vals, "tags": tags, "flat": flat, "flat_vals": flat_vals, "labels": labels, "vt_labels": vt_labels}


def jsonable(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return int(v)
    return v


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        if not rows:
            return
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else jsonable(v)) for k, v in r.items()})


def write_json(data, v, version, released, path):
    doc = {"name": "fungal_characters", "version": version, "released": released, "license": LICENSE, "license_url": LICENSE_URL,
           "homepage": "https://fungalcharacters.org/", "id_base": BASE,
           "identifiers": "Character codes FCC#####, value option codes FCV##### are permanent and never reused.",
           "parts": [{"id": r["id"], "name": r["name"], "description": r["description"]} for r in data["parts"]],
           "observation_methods": [{"id": r["id"], "name": r["name"], "description": r["description"]} for r in data["observation_methods"]],
           "fungus_types": [{"id": r["id"], "name": r["name"], "description": r["description"]} for r in data["fungus_types"]],
           "value_types": [{"id": r["id"], "key": r["name"], "name": v["vt_labels"].get(r["id"]), "description": r["description"],
                            "labels": v["labels"].get(("DisplayOption", r["id"]), [])} for r in data["display_options"]],
           "characters": []}
    for c, f in zip(data["mr_characters"], v["flat"]):
        p = c["properties"] or {}
        doc["characters"].append({
            "code": c["code"], "name": c["name"], "scientific_name": f["scientific_name"], "definition": c["description"],
            "part": f["part"], "observation_method": f["observation_method"], "value_type": f["value_type"],
            "value_type_label": f["value_type_label"], "unit": f["unit"],
            "applies_to_fungus_types": v["tags"].get(c["id"], []), "starter_set": bool(p.get("common")),
            "xde_lines": p.get("xde_lines", []), "source": f["source"], "comments": c["comments"],
            "labels": v["labels"].get(("MrCharacter", c["id"]), []),
            "value_options": [{"code": o["code"], "name": o["name"], "definition": o["description"],
                               "labels": v["labels"].get(("LookupItem", o["id"]), [])} for o in v["vals"].get(c["id"], [])]})
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def write_skos(data, v, version, path):
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import DCTERMS, RDF, SKOS
    FC = Namespace(BASE)
    g = Graph()
    g.bind("skos", SKOS); g.bind("dcterms", DCTERMS); g.bind("fc", FC)
    scheme = FC["scheme"]
    g.add((scheme, RDF.type, SKOS.ConceptScheme))
    g.add((scheme, SKOS.prefLabel, Literal("Fungal Characters", lang="en")))
    g.add((scheme, DCTERMS.hasVersion, Literal(version)))
    g.add((scheme, DCTERMS.license, URIRef(LICENSE_URL)))
    for p in data["parts"]:
        col = FC[f"part-{p['id']}"]
        g.add((col, RDF.type, SKOS.Collection)); g.add((col, SKOS.prefLabel, Literal(p["name"], lang="en")))
    for c, f in zip(data["mr_characters"], v["flat"]):
        u = FC[c["code"]]
        g.add((u, RDF.type, SKOS.Concept)); g.add((u, SKOS.inScheme, scheme)); g.add((u, SKOS.notation, Literal(c["code"])))
        for l in v["labels"].get(("MrCharacter", c["id"]), []):
            prop = {"name": SKOS.prefLabel, "scientific_name": SKOS.altLabel, "definition": SKOS.definition}.get(l["type"])
            if prop is None or (l["type"] == "scientific_name" and l["text"] == c["name"]):
                continue
            g.add((u, prop, Literal(l["text"], lang=l["language"])))
        if f["unit"]:
            g.add((u, SKOS.scopeNote, Literal(f"Unit: {f['unit']}", lang="en")))
        g.add((u, SKOS.scopeNote, Literal(f"Part: {f['part']}. Method: {f['observation_method']}. Value type: {f['value_type_label'] or f['value_type']}.", lang="en")))
        if c["part_id"]:
            g.add((FC[f"part-{c['part_id']}"], SKOS.member, u))
        if v["vals"].get(c["id"]):
            vc = FC[f"{c['code']}-values"]   # link name kept from 1.0.0 so existing links keep working
            g.add((vc, RDF.type, SKOS.Collection)); g.add((vc, SKOS.prefLabel, Literal(f"{c['name']} value options", lang="en")))
            g.add((u, SKOS.related, vc))
            for o in v["vals"][c["id"]]:
                vu = FC[o["code"]]
                g.add((vu, RDF.type, SKOS.Concept)); g.add((vu, SKOS.inScheme, scheme)); g.add((vu, SKOS.notation, Literal(o["code"])))
                for l in v["labels"].get(("LookupItem", o["id"]), []):
                    prop = {"name": SKOS.prefLabel, "definition": SKOS.definition}.get(l["type"])
                    if prop:
                        g.add((vu, prop, Literal(l["text"], lang=l["language"])))
                g.add((vc, SKOS.member, vu))
    g.serialize(str(path), format="turtle")


def write_sdd(data, v, version, released, path):
    from lxml import etree
    U = "http://rs.tdwg.org/UBIF/2006/"
    XML = "{http://www.w3.org/XML/1998/namespace}"

    def E(tag, parent=None, **a):
        attrs = {k: str(x) for k, x in a.items()}
        return etree.SubElement(parent, f"{{{U}}}{tag}", attrs) if parent is not None else etree.Element(f"{{{U}}}{tag}", attrs, nsmap={None: U})

    def rep(parent, label, detail=None):
        r = E("Representation", parent); l = E("Label", r); l.text = label or ""
        if detail:
            d = E("Detail", r); d.text = detail
        return r
    root = E("Datasets")
    tm = E("TechnicalMetadata", root, created=f"{released}T00:00:00")
    E("Generator", tm, name="fungalcharacters.org release export", version=version)
    ds = E("Dataset", root); ds.set(XML + "lang", "en")
    rep(ds, f"Fungal Characters v{version}", f"Character definitions for describing fungi. Codes are permanent identifiers "
        f"({BASE}<code>). License: {LICENSE} ({LICENSE_URL}), free to use in any way. {cite(version)}")
    chars_el = E("Characters", ds)
    CATEG = {"radio", "drop_down", "drop-down", "checkbox", "abundance", "taste", "odor", "texture"}   # keys; drop-down until 1.0.0
    QUANT = {"text_box_number_mm", "text_box_number_um", "text_box_number", "text_box_range_um"}
    BOOL = {"boolean_yes_no": ["Yes", "No"], "boolean_true_false": ["True", "False"], "boolean_present_absent": ["Present", "Absent"]}
    for c, f in zip(data["mr_characters"], v["flat"]):
        d = f["value_type"]; vs = v["vals"].get(c["id"], [])
        detail = c["description"] or None
        if d in BOOL or (d in CATEG and vs):
            ce = E("CategoricalCharacter", chars_el, id=c["code"]); rep(ce, c["name"], detail)
            st = E("States", ce)
            if vs:
                for o in vs:
                    s = E("StateDefinition", st, id=o["code"]); rep(s, o["name"], o["description"] or None)
            else:
                for nm in BOOL[d]:
                    s = E("StateDefinition", st, id=f"{c['code']}-{nm.lower()}"); rep(s, nm)
        elif d in QUANT:
            ce = E("QuantitativeCharacter", chars_el, id=c["code"]); rep(ce, c["name"], detail)
            if f["unit"]:
                mu = E("MeasurementUnit", ce); l = E("Label", mu); l.text = f["unit"]
        else:
            ce = E("TextCharacter", chars_el, id=c["code"]); rep(ce, c["name"], detail)
    etree.ElementTree(root).write(str(path), xml_declaration=True, encoding="UTF-8", pretty_print=True)


def write_xlsx(data, v, version, released, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    F = Font(name="Arial", size=10); H = Font(name="Arial", size=10, bold=True, color="FFFFFF"); HF = PatternFill("solid", start_color="305496")
    wb = Workbook(); ws = wb.active; ws.title = "README"
    for line in [f"Fungal Characters — release {version} ({released})", "",
                 "Characters: one row per character. Value options: every value option of every character.",
                 "Codes (FCC#####, FCV#####) are permanent and never reused; cite them when linking data.",
                 "Labels: names, scientific names and definitions by language (translations written on fungalcharacters.org).",
                 'Applies to fungus types: blank or "All" means the character applies to all fungi.',
                 "Other formats in this release: CSV, JSON, SQL for MySQL 8 and for PostgreSQL 16/17, SKOS (Turtle), SDD (TDWG XML).",
                 f"Web address for any code: {BASE}<code>, e.g. {BASE}FCC00019",
                 f"License: {LICENSE} ({LICENSE_URL}), free to use in any way.", cite(version)]:
        ws.append([line])
    ws["A1"].font = Font(name="Arial", size=12, bold=True)
    ws.column_dimensions["A"].width = 110

    def sheet(title, rows, widths=None):
        s = wb.create_sheet(title)
        if not rows:
            return
        hdr = list(rows[0].keys()); s.append(hdr)
        for r in rows:
            s.append([json.dumps(r[k], ensure_ascii=False) if isinstance(r[k], (dict, list)) else jsonable(r[k]) for k in hdr])
        for cell in s[1]:
            cell.font, cell.fill = H, HF
        for i, h in enumerate(hdr, 1):
            s.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, 18)
        s.freeze_panes = "B2"; s.auto_filter.ref = s.dimensions
    sheet("Characters", v["flat"], {"name": 34, "scientific_name": 34, "definition": 60, "value_options": 60, "source": 40, "comments": 40})
    sheet("Value options", v["flat_vals"], {"character": 34, "value_option": 34, "definition": 60})
    sheet("Labels", data["labels"], {"text": 60})
    for t in ["parts", "observation_methods", "display_options", "fungus_types", "character_fungus_types", "source_data", "releases"]:
        sheet(t, data[t])
    wb.save(str(path))


# ---------- notes ----------

def compare(prev_json, doc):
    """What changed since the previous release (by permanent code)."""
    if not prev_json or not prev_json.exists():
        return None
    old = json.loads(prev_json.read_text(encoding="utf-8"))
    def index(d):
        chars = {c["code"]: c for c in d["characters"]}
        vals = {o["code"]: o for c in d["characters"] for o in c.get("value_options", c.get("values", []))}
        return chars, vals
    oc, ov = index(old); nc, nv = index(doc)
    changed = [k for k in nc if k in oc and (nc[k]["name"], nc[k]["definition"]) != (oc[k]["name"], oc[k]["definition"])]
    langs = {}
    for c in doc["characters"]:
        for l in c["labels"]:
            if l["language"] != "en" and l["type"] == "name":
                langs[l["language"]] = langs.get(l["language"], 0) + 1
    return {"chars_added": sorted(set(nc) - set(oc)), "chars_removed": sorted(set(oc) - set(nc)), "chars_changed": changed,
            "vals_added": sorted(set(nv) - set(ov)), "vals_removed": sorted(set(ov) - set(nv)), "translated_names": langs}


def write_readme(version, released, doc, n_vals, path):
    path.write_text(f"""# Fungal Characters — release {version} ({released})

A reference list of characters (observable features) used to describe and identify fungi: {len(doc['characters'])} characters and {n_vals} value options.
Made from the live, publicly maintained data at https://fungalcharacters.org/.

## Files
| File | For |
|---|---|
| fungal_characters_v{version}.xlsx | Anyone: browse in Excel or Numbers |
| csv/characters_flat.csv, csv/value_options_flat.csv | Anyone: one row per character / per value option |
| csv/*.csv (other files) | One file per database table |
| fungal_characters_v{version}.json | Programmers |
| fungal_characters_v{version}.sql | Websites and databases (MySQL 8) |
| fungal_characters_v{version}_postgresql.sql | Websites and databases (PostgreSQL 16/17) |
| fungal_characters_v{version}_skos.ttl | Vocabulary tools (W3C SKOS, Turtle) |
| fungal_characters_v{version}_sdd.xml | Identification-key tools (TDWG SDD 1.1) |

## Identifiers
Each character has a permanent code (FCC#####) and each value option a permanent code (FCV#####). Codes are never reused
or changed. Each code's permanent web address is {BASE}<code>, e.g. {BASE}FCC00019 (Cap Width).

## Names and languages
Every character has an English name and a scientific name, plus a definition where available. Translations written by
volunteers on fungalcharacters.org are included in the labels table, by language.

## License and citation
{LICENSE} (public domain dedication, {LICENSE_URL}). Free to use in any way, including commercially, with no permission or credit required.
{cite(version)}
""", encoding="utf-8")


def write_changelog(version, released, notes, diff, prev_changelog, path, renamed_downloads=False, vt_notes=None):
    lines = [f"# Changelog", "", f"## {version} — {released}"]
    if notes:
        lines.append(notes)
    if diff:
        def few(codes):
            return ", ".join(codes[:20]) + (f" … ({len(codes)} in all)" if len(codes) > 20 else "")
        lines.append(f"- Characters: {len(diff['chars_added'])} added, {len(diff['chars_changed'])} with a changed name or definition, "
                     f"{len(diff['chars_removed'])} removed (codes stay retired, never reused).")
        if diff["chars_added"]:
            lines.append(f"  - Added: {few(diff['chars_added'])}")
        if diff["chars_removed"]:
            lines.append(f"  - Removed: {few(diff['chars_removed'])}")
        lines.append(f"- Value options: {len(diff['vals_added'])} added, {len(diff['vals_removed'])} removed.")
        if diff["translated_names"]:
            lines.append("- Translated character names: " + ", ".join(f"{k} {n}" for k, n in sorted(diff["translated_names"].items())) + ".")
    lines.append("- Downloads now say \"value options\" and \"value type\": columns value_options, value_option_code, value_option, "
                 "value_type; Excel sheet \"Value options\"; file csv/value_options_flat.csv (was values_flat.csv).") if renamed_downloads else None
    for note in (vt_notes or []):
        lines.append(note)
    previous = ""
    if prev_changelog and prev_changelog.exists():
        previous = prev_changelog.read_text(encoding="utf-8").split("\n", 1)[1].lstrip("\n")
    path.write_text("\n".join(l for l in lines if l is not None) + "\n\n" + previous, encoding="utf-8")


def value_type_notes(prev_dir, data):
    """Changelog lines about value types: renamed keys, and display names added (compared with the previous release)."""
    notes = []
    old = {}
    path = prev_dir / "csv" / "display_options.csv"
    if path.exists():
        with open(path, encoding="utf-8-sig") as f:
            old = {int(r["id"]): r["name"] for r in csv.DictReader(f)}
    renamed = [f"{old[r['id']]} → {r['name']}" for r in data["display_options"] if r["id"] in old and old[r["id"]] != r["name"]]
    if renamed:
        notes.append("- Value type keys renamed: " + ", ".join(renamed) + ".")
    prev_labels = prev_dir / "csv" / "labels.csv"
    had_names = prev_labels.exists() and "DisplayOption" in prev_labels.read_text(encoding="utf-8-sig")
    if not had_names and any(l["labelable_type"] == "DisplayOption" for l in data["labels"]):
        notes.append("- Value types now have display names (labels table, type DisplayOption; new column value_type_label "
                     "next to value_type). The keys in value_type stay permanent.")
    return notes


# ---------- the whole release ----------

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def build_release(version, released, notes="", out_root=None, previous=None):
    """Write data/releases/<version>/ (or out_root/<version>/). Returns a summary dict."""
    if not VERSION_RE.match(version):
        raise ValueError("Version must look like 1.1.0")
    out_root = Path(out_root or RELEASES_DIR)
    out = out_root / version
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} already exists and is not empty")
    previous = previous or sorted((p.name for p in RELEASES_DIR.iterdir() if p.is_dir() and VERSION_RE.match(p.name)),
                                  key=lambda s: tuple(map(int, s.split("."))))[-1]
    prev_dir = RELEASES_DIR / previous
    (out / "csv").mkdir(parents=True, exist_ok=True)
    data = read_tables()
    left_out = drop_hidden(data)
    # The new release's own row in the releases table.
    if not any(r["version"] == version for r in data["releases"]):
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        data["releases"].append({"id": max((r["id"] for r in data["releases"]), default=0) + 1, "version": version,
                                 "released_at": datetime.date.fromisoformat(released), "notes": notes or None,
                                 "created_at": now, "updated_at": now})
    stem = f"fungal_characters_v{version}"
    v = build_views(data)
    write_postgresql(data, version, prev_dir / f"fungal_characters_v{previous}_postgresql.sql", out / f"{stem}_postgresql.sql")
    write_mysql(data, version, prev_dir / f"fungal_characters_v{previous}.sql", out / f"{stem}.sql")
    write_csv(out / "csv" / "characters_flat.csv", v["flat"])
    write_csv(out / "csv" / "value_options_flat.csv", v["flat_vals"])
    for t in TABLES:
        write_csv(out / "csv" / f"{t}.csv", data[t])
    doc = write_json(data, v, version, released, out / f"{stem}.json")
    write_skos(data, v, version, out / f"{stem}_skos.ttl")
    write_sdd(data, v, version, released, out / f"{stem}_sdd.xml")
    write_xlsx(data, v, version, released, out / f"{stem}.xlsx")
    diff = compare(prev_dir / f"fungal_characters_v{previous}.json", doc)
    write_readme(version, released, doc, len(v["flat_vals"]), out / "README.md")
    write_changelog(version, released, notes, diff, prev_dir / "CHANGELOG.md", out / "CHANGELOG.md",
                    renamed_downloads=(prev_dir / "csv" / "values_flat.csv").exists(),
                    vt_notes=value_type_notes(prev_dir, data))
    return {"out": str(out), "previous": previous, "characters": len(data["mr_characters"]),
            "value_options": len(data["lookup_items"]), "labels": len(data["labels"]), "left_out_hidden": left_out, "diff": diff}
