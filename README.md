# World Cup Club Bragging Board

Ranks clubs from Europe's big-five leagues plus MLS by how their players perform
at the FIFA World Cup 2026. Static site, rebuilt every ~15 minutes via GitHub Actions.

## How it works
1. `src/mapping.py` builds an athlete-id → club map from domestic rosters
   (`?season=2025` is required — endpoints are empty otherwise).
2. `src/wc_stats.py` collects WC match summaries and accumulates per-player
   stats, minutes and clean sheets.
3. `src/rating.py` computes a position-aware rating per player (weights in
   `src/weights.py`), `src/aggregate.py` rolls clubs up four ways
   (Total / Average / Per-90 / Best XI).
4. `src/build.py` writes `web/standings.json`; the page renders it client-side.

## Develop
```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q                          # run tests
python3 -m src.build                          # regenerate web/standings.json (needs network)
python3 -m http.server 8000 --directory web   # preview at http://localhost:8000
```

To refresh the offline test fixtures: `python3 tests/capture_fixtures.py`.

## Tuning the scoring
Edit `src/weights.py` — it is the single source of truth for the rating model.

## Caveat
Uses unofficial ESPN endpoints; shapes can change. The pipeline fails soft and
keeps the last good `standings.json`.
