# Static site

A pure HTML/JS/CSS dashboard that mirrors the Streamlit app's
disease-forecast view. Designed to deploy to **GitHub Pages** with no
backend — all data is generated daily by a Python build script that
hits the same APIs the Streamlit app uses.

```
site/
├── index.html              entry page
├── lib/
│   ├── app.js              boot + controller
│   ├── biomass.js          biomass NLS model (port of Python)
│   ├── map.js              Leaflet map + station markers
│   └── render.js           metric tiles, model-info, station table
├── assets/                 UW brand CSS + logos (copied by build_site.py)
└── data/
    └── latest.json         daily snapshot (built by build_site.py)
```

## Build the data

From the **project root** (one level up from `site/`):

```bash
python build_site.py                 # uses defaults (yesterday + Sep 15 planting)
python build_site.py 2026-05-19      # specific forecasting date
python build_site.py 2026-05-19 2025-09-20   # ... and planting date
```

This writes `site/data/latest.json` (~50 KB for ~70 stations) and
copies the UW logos into `site/assets/`.

## Preview locally

```bash
cd site
python -m http.server 8000
# open http://localhost:8000
```

The browser must be served over HTTP for `fetch("data/latest.json")` to
work — opening `index.html` directly with `file://` will fail.

## Deploy to GitHub Pages

1. Push the repo to GitHub.
2. **Settings → Pages**: set "Source" to *Deploy from a branch*, branch
   `main`, folder `/site`.
3. The included workflow `.github/workflows/build-data.yml` runs
   `build_site.py` once a day, commits the refreshed JSON, and Pages
   picks it up automatically.

## Adding a new disease model

Add an entry to `DISEASE_OPTIONS` in `features/config.py` and rerun
`python build_site.py` — the static site's model selector reads the
list straight out of the JSON, so no JS changes are needed.
