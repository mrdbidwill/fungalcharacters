# Plan for other languages (internationalization)

Status 2026-11-25 (afternoon): framework built. All page text is marked for translation (285 messages); translation
files exist for Spanish, Thai, Portuguese (Brazil) and French; the Languages page shows progress and lets anyone preview;
signed-in volunteers translate character data on the site. English is the only published language. How to help:
docs/TRANSLATING.md.

There are two separate things to translate:

1. **The website's own words** (menus, buttons, page text, messages, emails).
2. **The character data** (character names, definitions, value options), which the community writes.

The common / scientific-name switch is a third, separate thing. It works in every language (common names in the reader's language).

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
   Done 2026-11-25. New text is marked as it is written (rule in CLAUDE.md) and the translation files refreshed.
2. Done: translation files `locale/<lang>/LC_MESSAGES/django.po` and template `locale/django.pot`.
3. Translate them (see "Who translates").
4. Done: the 🌐 Languages page in the header. A choice is remembered in the browser (cookie); first visits follow the
   browser's language among published languages. (Saving the choice in the account: later, if wanted.)
5. Re-run the accessibility audit in each language (docs/ACCESSIBILITY.md).

Web addresses: permanent codes stay language-free (`/id/FCC00019` is the same everywhere).
No language prefix in addresses (language from the visitor's choice, or the browser among published languages). Add
`/es/…`-style prefixes later only if search engines need separate language pages.

## 2. The character data

The data release already stores names, scientific names and definitions per language in the `labels` table
(`language` column; English is `en`). So no database change is needed.

Plan:
- Done: a "Translate" page per character (name, definition and every value option at once), reached from the
  character page or "Translate characters" (next untranslated). Each translation records who wrote it and is in the
  public history. (A source for a translation: later, if wanted.)
- Done: pages show the reader's language where a translation exists (with the English name too), and English
  otherwise, with `lang="en"` so screen readers switch voice.
- Done: searching finds characters by any language's name.
- Downloads and releases include every language (they already carry the `language` column).
- Scientific (Latin) names are shared by all languages and are not translated.

## Which languages first — decided (Will, 2026-11-25)

Spanish, Thai, Portuguese (Brazil), French — as suggested:
- **Spanish**: Mexico and Latin America (the Guzmán tradition), large iNaturalist community.
- **Thai**: nolo_mode's myceliome.com community.
- **Portuguese** (Brazil) and **French**: large mycological communities.

## Who translates — decided (Will, 2026-11-25): volunteers, with a supportive framework

- **Website words:** volunteers through **Weblate** (free hosting for open-source projects; it works on the
  `.po` files in the GitHub repository, with review). Or people send corrections and Claude applies them.
- **Character data:** community members on the site itself (section 2).
- Machine translation may be used only as a first draft that a person reviews; drafts are never shown as final.
