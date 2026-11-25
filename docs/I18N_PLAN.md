# Plan for other languages (internationalization)

Status 2026-11-25: groundwork in place; English only. Decisions still needed from Will are marked **Decide**.

There are two separate things to translate:

1. **The website's own words** (menus, buttons, page text, messages, emails).
2. **The character data** (character names, definitions, value options), which the community writes.

The English / scientific-name switch is a third, separate thing. It stays as it is and works in every language.

## 1. The website's own words

Already done (2026-11-25):
- Django's language system is switched on (`LocaleMiddleware`, `LANGUAGES`, `locale/` folder).
- Every page declares its language and text direction (`<html lang=… dir=…>`), so screen readers pronounce text
  correctly and right-to-left languages (Arabic, Hebrew, Persian) will lay out correctly.
- The stylesheet uses direction-neutral rules (start/end instead of left/right).
- The typeface covers Latin and accented Latin (most European languages, Vietnamese, Turkish, …). Other scripts
  (Greek, Cyrillic, Thai, Chinese, …) use the reader's system font, which is the most legible choice for them.
- The account pages (django-allauth) already come translated into about 50 languages.

Next steps (when the first language is chosen):
1. Mark every piece of page text for translation (`{% translate %}` in templates, `gettext` in Python).
   Claude does this in one pass and adds a test that fails if new untranslated text appears.
2. Generate the translation files (`locale/<lang>/LC_MESSAGES/django.po`).
3. Translate them (see "Who translates").
4. Add a language menu in the header. Choosing a language remembers it (cookie and account setting); first visits
   follow the browser's language.
5. Re-run the accessibility audit in each language (docs/ACCESSIBILITY.md).

Web addresses: permanent codes stay language-free (`/id/FCC00019` is the same everywhere).
**Recommended:** no language prefix in addresses at first (language from the menu choice or the browser). Add
`/es/…`-style prefixes later only if search engines need separate language pages. **Decide.**

## 2. The character data

The data release already stores names, scientific names and definitions per language in the `labels` table
(`language` column; English is `en`). So no database change is needed.

Plan:
- On each character and value option page, signed-in users can add or edit the name and definition **in their language**.
  Each translation records who wrote it, its source if any, and is in the public history, like everything else.
- Pages show the reader's language where a translation exists, and English otherwise, marked "(English)" and with
  `lang="en"` so screen readers switch voice.
- Searching finds characters by any language's name.
- Downloads and releases include every language (they already carry the `language` column).
- Scientific (Latin) names are shared by all languages and are not translated.

## Which languages first — **Decide**

Suggestion, based on who uses fungal data and the people already involved:
- **Spanish**: Mexico and Latin America (the Guzmán tradition), large iNaturalist community.
- **Thai**: nolo_mode's myceliome.com community.
- **Portuguese** (Brazil) and **French**: large mycological communities.

## Who translates — **Decide**

- **Website words:** volunteers through **Weblate** (free hosting for open-source projects; it works on the
  `.po` files in the GitHub repository, with review). Or people send corrections and Claude applies them.
- **Character data:** community members on the site itself (section 2).
- Machine translation may be used only as a first draft that a person reviews; drafts are never shown as final.
