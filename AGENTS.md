# Codex development rules

- Use Python 3.11+ and Flet. Keep game rules independent from controls.
- The product is portrait-first and must preserve drag-to-pair interaction.
- CSV is the source of truth. A failed or invalid CSV load returns to Home with an actionable error.
- Run `python -m pytest -q` before reporting a change complete.
- Do not add credentials or hard-code private URLs. Configure `CSV_URL` with an environment variable.

