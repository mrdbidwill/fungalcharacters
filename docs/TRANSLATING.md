# Translating Fungal Characters

Thank you for helping. There are two separate things to translate. You can help with either.

| What | Examples | Where you translate |
|---|---|---|
| **The character data** | "Cap Width", its definition, value options such as "Smooth" | On the site: sign in, open **🌐 Language** in the menu (the Languages page), choose **Translate characters** |
| **The website's own words** | menus, buttons, page text, messages | The translation platform (see below), or the `locale/` files in this repository |

Scientific (Latin) names are shared by every language and are not translated.

Languages being translated now: **Spanish (es), Thai (th), Portuguese — Brazil (pt-br), French (fr)**.
To add another language, ask (open a GitHub issue); it takes one line in `config/settings.py` and one command.

## 1. Translating the character data (on the site)
1. Sign up and sign in at https://fungalcharacters.org/.
2. Open the **Languages** page (🌐 in the menu) and choose **Translate characters** next to your language.
   You get the next character that has no name in that language yet.
3. For the character and each of its value options, write the name and, if you can, the definition as they are
   used in your language. The English text is shown above each box. Leave a box empty if you are unsure.
4. **Save and go to the next character**.

- Your translations are credited to you, listed on your account page, and kept in the public edit history.
- You can change your own translations later. A translation written by someone else is shown read-only;
  suggest changes to them or to the admin.
- Readers who chose your language see your translated names, with the English name shown as well.

## 2. Translating the website's words
The site uses standard gettext files: `locale/<language>/LC_MESSAGES/django.po` (template: `locale/django.pot`).

- **On the translation platform** (when it is set up; the Languages page links to it): translate in the browser;
  the platform sends your work to this repository.
- **Directly**: edit the `.po` file for your language (any PO editor, e.g. Poedit) and open a pull request.

Guidelines:
- Keep placeholders exactly: `%(name)s`, `%(n)d`, `{{ count }}` and HTML such as `<strong>…</strong>` or `<a href="…">`.
- "No advice about consumption." is a required notice on every page: translate its meaning exactly, short and plain.
- Character, value option, value type: see the Terms in docs/DECISIONS.md. A *value* is what one mushroom has;
  *value options* are a character's allowed choices.
- Keep the tone plain and short; many readers use screen readers or read in a second language.

## When a language goes live
A language appears in the site's language menu (and is offered to visitors whose browser prefers it) once Will
decides its translation is ready: Claude adds its code to `PUBLISHED_LANGUAGES` on the server. Until then anyone
can **Preview** it from the Languages page.

## For maintainers (Claude)
- Every new piece of page text is marked for translation: `{% translate %}` / `{% blocktranslate trimmed %}` in
  templates, `gettext` / `gettext_lazy` in Python.
- After changing page text: `docker compose exec web python manage.py makemessages -l es -l th -l pt_BR -l fr --keep-pot -i tools -i data -i staticfiles -i node_modules`,
  commit `locale/`, push. The platform picks up the new text.
- `.mo` files are not committed; they are compiled when the Docker image is built and when the dev container starts.
- Data translations live in the release table `labels` (`language` = the interface code, e.g. `es`, `pt-br`);
  who wrote each one is in `ItemMeta` (item type `Label`); changes are in the history.
- Publish a language: add it to `PUBLISHED_LANGUAGES` in the server's `.env`, restart the web container.
- Set the platform link: `TRANSLATION_PLATFORM_URL` in the server's `.env`.
