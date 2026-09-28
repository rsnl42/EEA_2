# PISA 2025: digital devices and AI in school

A small static site (for GitHub Pages) with interactive analyses of the OECD chapter 4 country
tables. `docs/index.html` is the landing page; every dashboard lives in its own folder and is
linked from it.

| Page | Path | Analysis script |
|---|---|---|
| Landing page | `docs/index.html` | (built from the `PAGES` list in `build_site.py`) |
| Who uses AI and devices, and who doesn't? (#1) | `docs/equity-gaps/` | `analysis/01_equity_gaps.py` |
| Which infrastructure divides actually exist? (#2) | `docs/infrastructure-divides/` | `analysis/02_infrastructure_divides.py` |
| Does guidance keep pace with AI use? (#7) | `docs/use-guidance/` | `analysis/07_use_guidance_gap.py` |
| How are schools governing devices and AI, and is it changing? (#8) | `docs/policy-typologies/` | `analysis/08_policy_typologies.py` |
| How do resources, capacity, time use and AI relate? (#9) | `docs/cross-domain/` | `analysis/09_cross_domain_panel.py` + `09b` + `09c` |

## Layout

```
build_site.py               builds everything into docs/ (landing + all dashboards)
build_dashboard.py          equity-gaps page  (also runnable alone)
build_use_guidance.py       use-guidance page (also runnable alone)
site_common.py              template loading / writing helpers
templates/                  base.css (shared styles), landing.html, equity_gaps.html, use_guidance.html
analysis/                   pisa_utils.py + one script per analysis (CSV/PNG outputs in outputs/)
data/                       digital_devices_AI_chapter4.xlsx
docs/                       generated site (committed, served by GitHub Pages)
.github/workflows/pages.yml optional: rebuild and deploy on every push to main
```

## Build and preview

```bash
pip install -r requirements.txt        # pandas, openpyxl, scipy
python build_site.py                   # writes docs/
python -m http.server -d docs 8000     # http://localhost:8000
```

Analysis scripts (matplotlib is needed for the PNG):

```bash
pip install -r requirements-analysis.txt
python analysis/01_equity_gaps.py
python analysis/02_infrastructure_divides.py
python analysis/07_use_guidance_gap.py
python analysis/08_policy_typologies.py
```

## Publish on GitHub Pages

1. **Deploy from a branch (simplest).** Commit `docs/`, then Settings > Pages > Source:
   "Deploy from a branch", branch `main`, folder `/docs`. The landing page is the site root.
2. **GitHub Actions.** Settings > Pages > Source: "GitHub Actions". The workflow runs
   `python build_site.py` on each push to `main` and deploys `docs/`. Bump action versions if
   GitHub flags them as deprecated.

Links between pages are relative (`equity-gaps/`, `../`), so the site works from a project
subpath such as `https://<user>.github.io/<repo>/`.

## Adding a dashboard

1. Write `analysis/NN_name.py` (reuse `pisa_utils.Workbook`), exposing the computation as functions.
2. Add `templates/<page>.html` (start its `<style>` with `%%BASE_CSS%%`, include a nav link back to
   `../`, and use `%%PLACEHOLDER%%` tokens for injected data) and `build_<page>.py` with
   `build(xlsx, out) -> str`.
3. Append an entry (slug, title, blurb, tables, script, build) to `PAGES` in `build_site.py`.
   The landing page and the `docs/<slug>/` folder follow automatically.

## Notes on the numbers

- Estimates and standard errors come straight from the workbook; "significant" means
  |estimate / S.E.| > 1.96 (or a 95% CI that excludes the reference).
- Group gaps are unadjusted, and country-level relationships are correlational (about 85 systems).
- The equity page keeps 4 decimals for S.E.s because index-point standard errors are ~0.01 to 0.05.
- Systems marked * carry comparability flags in the source.
- Google Fonts loads from the web; without network access pages fall back to system fonts.
