# Concept Matching Game

Python + Flet implementation of the concept matching elimination game.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flet run src/main.py --web
```

Set `CSV_URL` to a published CSV endpoint before starting. A sample URL is included in `.env.example`.

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

