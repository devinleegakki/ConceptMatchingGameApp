# Concept Matching Game

Python + Flet implementation of the concept matching elimination game.

Cards are fully visible from the beginning. Players drag two visible cards into the pairing zone below the grid; the game does not use hidden-card memory or click-to-select pairing.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
flet run src/main.py --web
```

When the Web preview tab is closed, the app exits the Flet process automatically after a short reconnect grace period, so the terminal command ends without requiring `Ctrl+C`. A quick browser refresh keeps the process alive.

The project defaults to the team's Google Sheets CSV endpoint. You can override it with `CSV_URL` before starting. The sheet must contain the schema below; an empty sheet produces a clear in-app error until content is added.

## CSV schema

`level,order,pair_id,type,content,explanation,duration_seconds`

The `content` field is displayed directly on the card. Edit `content` in Google Sheets to change the question or formula; the app does not rewrite, shorten, or replace it. `explanation` is shown after a successful pair.

Each level must contain 8 cards (level 1) or 12 cards (level 2), and every pair id must occur exactly twice.

## Test

```powershell
python -m pytest -q
```

## Android

The app intentionally keeps the CSV endpoint configurable so the same build can point at a team's published sheet. Set it in the build environment when needed; do not hard-code credentials or private URLs into the app.

### Build prerequisites

- Python 3.11+ (the verified build used Python 3.12)
- Flet 1.1.2
- Flutter 3.47.9
- JDK 17
- Android SDK and Android build tools

Flet can install or download missing JDK and Android SDK components during the first build, but the machine must have network access and permission to install them.

### Standard APK build

Run these commands from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q

# Optional: configure the CSV source for this build/session.
$env:CSV_URL = "https://example.invalid/export.csv"

$env:PYTHONIOENCODING = "utf-8"
$env:FLET_CLI_LOG_FORMAT = "plain"
flet build apk --yes --no-rich-output --skip-flutter-doctor `
  -o build\apk `
  --project concept_match `
  --product ConceptMatch `
  --description ConceptMatch
```

The APK is written to `build/apk/concept_match.apk`; the matching SHA-1 file is written beside it. Check the artifact and calculate a stronger delivery checksum with:

```powershell
Get-Item build\apk\concept_match.apk
Get-FileHash build\apk\concept_match.apk -Algorithm SHA256
```

### Windows path and terminal notes

Android Gradle builds can fail when the project path contains non-ASCII characters. The failure usually contains:

```text
Your project path contains non-ASCII characters.
```

If that happens, copy the project to a temporary ASCII-only directory (for example `C:\concept_match_build`), run the same `flet build apk` command there, and copy `build\apk\concept_match.apk` plus its `.sha1` file back to this project's `build\apk` directory. Do not commit the temporary directory or generated build caches.

On Windows, Flet's rich output can also hit a GBK encoding error. Setting `PYTHONIOENCODING=utf-8` and `FLET_CLI_LOG_FORMAT=plain` as shown above avoids that terminal-output problem.

### Build verification

Always run the test suite before reporting a build complete:

```powershell
python -m pytest -q
```

The verified build completed with `23 passed`. The resulting APK was approximately 172 MB. The APK build itself does not validate the remote CSV contents; verify that `CSV_URL` is reachable and that the CSV follows the schema above when testing the installed app.

