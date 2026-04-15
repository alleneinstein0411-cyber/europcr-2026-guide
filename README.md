# EuroPCR 2026 Guide

Personal offline-first PWA for navigating EuroPCR 2026 (19–22 May, Paris).

## Features

- **Three-day curated schedule** (Tue / Wed / Thu) with backup options per block
- **60 researched speaker cards** with expertise, key publications, PMIDs
- **8 trial intelligence cards** (LBT + Hotline + landmark trials)
- **In-app edit UI** — swap backups, add notes, tag sessions (no code editing needed)
- **Offline-first** — works completely offline after first load (Service Worker)
- **PWA installable** — add to home screen, looks/feels like a native app
- **547 session search** across all three days

## Structure

```
.
├── app/                    # The deployed web app (served by GitHub Pages)
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── sw.js               # service worker
│   ├── manifest.webmanifest
│   ├── icons/
│   └── data/               # bundled app data (built from app-data/)
├── app-data/               # Source data (curated + extracted)
│   ├── sessions_all_v2.json
│   ├── speakers/           # 60 researched speakers in 11 batches
│   ├── trials/
│   ├── schedule_final.json # Dr. Chang's curated schedule
│   └── manifest.json       # project status
└── scripts/
    ├── build-data.py       # rebuilds app/data/ from app-data/
    ├── check-update.py     # checks EuroPCR PDF for updates (TODO)
    ├── diff-schedule.py    # diffs schedule after extraction (TODO)
    └── make-icons.py       # generates PWA icons
```

## Building

After editing any file in `app-data/`:

```bash
python3 scripts/build-data.py
```

This regenerates `app/data/*.json` from the source data.

## Local preview

```bash
cd app
python3 -m http.server 8731
# open http://localhost:8731
```

## Maintenance

See [MAINTENANCE.md](MAINTENANCE.md) for update scenarios before/during the conference.

---

*Built by Claude + Dr. Chang, April 2026*
