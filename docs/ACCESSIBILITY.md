# Accessibility

Standard: WCAG 2.2, level AA everywhere, and AAA contrast (at least 7:1) for all text in light and dark modes.
Readability for people with sight issues comes first (docs/DECISIONS.md, "Look and accessibility").

## What the site does
- Typeface Atkinson Hyperlegible (designed for low-vision readers); 18px base text that grows with the browser's text size.
- AAA contrast for all text, links and buttons in both colour schemes; field borders and focus outlines at least 3:1.
- Links always underlined; a thick amber focus outline; a "Skip to content" link; the current page marked in the menu (`aria-current`).
- Large click targets (44px buttons and fields), larger checkboxes.
- Follows the reader's settings: light/dark, more contrast (`prefers-contrast`), reduced motion, Windows high-contrast (`forced-colors`).
- Every form field has a label (visually hidden where the purpose is obvious on screen); every table column has a header.
- No hidden "honeypot" fields: screen readers can reach them and would trap blind users.
- Consistent wording: "Sign in", "Sign up", "Sign out" everywhere.

## Automated audit (run after any change to pages or styles)
Tool: `tools/a11y/audit.js` (axe-core 4.10.3 driven through Chrome). It checks every rule tagged WCAG 2.0/2.1/2.2 A, AA,
AAA and best-practice, in light and dark mode.

Last run 2026-11-25: 24 pages × 2 colour schemes = 48 page views, **0 violations**
(public pages, character, history, value type, source, downloads, thanks, sign-in, sign-up, password reset; and,
signed in: account, add character / value option / value type / source, email, password, two-factor, sessions).
Not audited: Django's own admin pages (used only by the admin).

How to run (Claude runs it): start Chrome headless with `--remote-debugging-port=9333`, then
`cd tools/a11y && npm install && node audit.js 9333 http://localhost:8000 - / /characters/ ...`
(pass a session id instead of `-` to audit signed-in pages).

## Checked by hand
- Layout at phone width (no sideways scrolling except inside wide data tables, which scroll on their own).
- Keyboard: every link, button and field reachable in order; focus always visible.

## Still to do
- Test with VoiceOver (Mac/iPhone) and NVDA (Windows) before launch.
- Re-run the audit when other languages are added (see docs/I18N_PLAN.md).
