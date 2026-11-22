# Concept Matching Game

Python + Flet implementation of the concept matching elimination game.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flet run src/main.py --web
```

The project defaults to the team's Google Sheets CSV endpoint. You can override it with `CSV_URL` before starting. The sheet must contain the schema below; an empty sheet produces a clear in-app error until content is added.

## CSV schema

`level,order,pair_id,type,content,explanation,duration_seconds`

Each level must contain 8 cards (level 1) or 12 cards (level 2), and every pair id must occur exactly twice.

## Test

```powershell
python -m pytest -q
```

## Android

```powershell
flet build apk
```

The app intentionally keeps the CSV endpoint configurable so the same build can point at a team's published sheet.

