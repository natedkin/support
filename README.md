# Support site

Support, privacy and contact pages for apps by Nathan Edkin, published at
https://natedkin.github.io/support/

Everything is generated from one data file, `apps.json`, by `build.py`.
GitHub Pages serves the `docs/` folder on the `main` branch.

## Add or update an app

1. Add the icon: a square PNG (256 x 256 is plenty) at `assets/icons/<slug>.png`.
   Optional wide header art goes in `assets/headers/<slug>.jpg` (about 1600 x 686).
2. Edit `apps.json` and add an entry to `apps` (copy an existing one). Key fields:
   - `slug`: URL name. Pages are `/support/apps/<slug>/` and `/support/privacy/<slug>/`
   - `aliases`: old slugs that should also work (pages are copied there)
   - `store_id`: the App Store numeric id (the number after `id` in the App Store link)
   - `live`: `true` shows the App Store button; `false` shows "Coming soon"
   - `version`, `category`, `tagline`, `summary`, `intro`, `lists`, `pricing`, `faq`
   - `purchases`: names of the in-app purchases
   - `data`: privacy flags (ads, tracking prompt, consent form, iCloud, subscription...)
   - `privacy.updated`: the policy's last-updated date (YYYY-MM-DD)
   - `privacy.sections`: the policy text. Changes and Contact are added automatically.
     Links can be written as `[label](https://example.com)`.
3. Build: `python3 build.py` (Python 3, no packages needed).
4. Check locally if you like: `python3 -m http.server -d docs 8000`, then open
   http://localhost:8000/ (links use the `/support` prefix, so test paths on the live site).
5. Publish: `git add -A && git commit -m "Update <app>" && git push`.
   GitHub Pages redeploys in a minute or two.

## Rules for content

- Privacy pages must match what the shipped build actually does (ads, tracking prompt,
  purchases, iCloud, permissions).
- Contact address is natedkinsupport@gmail.com only.
- Nothing secret goes in this repo.
