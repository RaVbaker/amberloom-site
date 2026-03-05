# amberloom-site
Webpage for amberloom app

## Localization and shared config

- The landing page supports three locales: English (`en`), Polish (`pl`), and Dutch (`nl`).
- Copy is managed in the `translations` object in `index.html` and mapped via `data-i18n` / `data-i18n-html` attributes.
- Common links are centralized in `LINKS` (`appStore`, `privacy`, `support`) and wired through CSS hooks:
  - `.js-download-link`
  - `.js-privacy-link`
  - `.js-support-link`

### Language selection

- Users can switch language from the nav dropdown.
- Locale precedence: `?lang=` query parameter → `localStorage` (`amberloom-lang`) → browser locale fallback from `navigator.languages` / `navigator.language` (normalized to `en`/`pl`/`nl`).
