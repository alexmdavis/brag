# Logos/Flags + Scoring Explainer — Design Spec

**Date:** 2026-06-16
**Status:** Approved design, pending spec review
**Builds on:** the shipped World Cup Club Bragging Board (`~/Projects/brag`, live at
https://alexmdavis.github.io/brag/).

## 1. Overview

Two additive features on the existing pipeline + static page:

- **A. Logos & flags** — league logos, club crests, national flags, and player
  headshots shown in the table headers and entries.
- **B. Scoring explainer** — an in-page collapsible "How scoring works" panel,
  generated from `src/weights.py` so it always matches the live scoring model.

Neither feature changes the architecture. Both extend the existing pattern:
the pipeline computes everything into `web/standings.json`, and the static page
renders it client-side. No new network requests are added to the hot path
(except the browser loading images from ESPN's CDN).

## 2. Data sources (all verified live 2026-06-16, all free from ESPN CDN)

| Asset | Source | URL shape | Coverage |
|---|---|---|---|
| Club crest | `roster.team.logo` (already fetched in mapping) | `…/teamlogos/soccer/500/{teamId}.png` | full |
| National flag | WC summary `rosters[].team.logos[].href` (already fetched) | `…/teamlogos/countries/500/{abbr}.png` (+ `500-dark` variant) | full |
| League logo | static map (no per-request source in the data we fetch) | `…/leaguelogos/soccer/500/{n}.png` | full |
| Player headshot | derived from athlete id | `…/headshots/soccer/players/full/{id}.png` | **partial (~50–60%)** |

Verified league logo ids (HTTP 200): `eng.1`→23, `esp.1`→15, `ita.1`→12,
`fra.1`→9, `ger.1`→10.

**Headshot coverage is partial** (sampled 4/8; the resize "combiner" endpoint
also 404s when the source is missing). Therefore headshots require a fallback
chain: **headshot → national flag → initials avatar**. Flags and crests have
full coverage, so the table never renders broken.

## 3. Feature A — logos & flags

### Pipeline changes
- **`src/config.py`**
  - `LEAGUE_LOGOS = {"eng.1": ".../23.png", "esp.1": ".../15.png", "ita.1": ".../12.png", "fra.1": ".../9.png", "ger.1": ".../10.png"}` (full URLs).
  - `HEADSHOT_URL = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"`.
- **`src/mapping.py`** — capture `clubLogo` (`roster.team.logo`, may be `None`)
  into each mapping entry: `{club, league, leagueName, position, clubLogo}`.
- **`src/wc_stats.py`** — in `process_match_summary`, capture per nation
  `nationFlag` from `team.logos[0].href` (first/`default` variant) and store it
  on each player record; derive `headshot` from `HEADSHOT_URL.format(id=pid)`.
  New record keys: `nationFlag`, `headshot`. (`clubLogo` carried from mapping
  info into the record.)

### `standings.json` additions
- club object: `clubLogo` (str|None), `leagueLogo` (str|None).
- player object: `nationFlag` (str|None), `headshot` (str|None).

`build.py` threads `clubLogo` and `leagueLogo` (from `config.LEAGUE_LOGOS`
keyed by club's league) into each club, and `nationFlag`/`headshot` into each
player.

### Frontend (`web/`)
- **League tabs:** small league logo before each league name (skip for "All").
- **Combined table:** club column shows crest + name (crest ~20px, circular/
  contained); league column shows the league logo (with the name as `alt`/title).
- **Expanded player rows:** a circular headshot at left (with fallback chain),
  and a small flag next to the nation in the meta line.
- All images: `loading="lazy"`, fixed width/height to avoid layout shift,
  `onerror` handler implementing the fallback (headshot→flag→initials; crest/
  flag/league→hide on error). Images built via safe DOM construction (no
  `innerHTML` of URLs).

## 4. Feature B — scoring explainer panel

### Pipeline changes
- **`src/methodology.py`** (new, pure) — `build_methodology(weights_module)`
  returns a JSON-serializable dict from the weights module:
  ```
  {
    "positionGroups": {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"},
    "weights": { "GK": {<field>: <points>, ...}, "DEF": {...}, ... },
    "cleanSheetBonus": {"GK": 4.0, ...},
    "appearancePoints": 0.5,
    "fieldLabels": {"totalGoals": "Goals", ...},
    "views": [
      {"key": "total",   "label": "Total",   "formula": "Sum of every player's rating."},
      {"key": "average", "label": "Average", "formula": "Mean rating across the club's WC players."},
      {"key": "per90",   "label": "Per-90",  "formula": "Total rating ÷ (total minutes ÷ 90)."},
      {"key": "bestXI",  "label": "Best XI", "formula": "Sum of the club's top 11 player ratings."}
    ],
    "notes": [
      "Players are attributed to their 2025–26 club.",
      "Stats come from completed/in-progress World Cup matches via ESPN.",
      "A clean sheet = a match the player featured in where his team conceded 0."
    ]
  }
  ```
- **`src/build.py`** — embed `assemble_standings(...)["methodology"] =
  build_methodology(weights)`. (Add `methodology` to the returned dict.)

### `standings.json` addition
- top-level `methodology` object (schema above).

### Frontend (`web/`)
- A **"How scoring works"** button in the header `controls`. Clicking toggles a
  collapsible `<section id="explainer">` (hidden by default) rendered from
  `DATA.methodology`:
  - A short intro line.
  - The four view formulas (label → formula).
  - A weights table: rows = stat labels (from `fieldLabels`, plus "Clean sheet"
    and "Appearance"), columns = GK/DEF/MID/FWD, cells = points (blank if a
    field is not weighted for that group).
  - The notes list + data-source/season line.
- Rendered via safe DOM construction. Toggling is pure client-side.

## 5. Architecture & isolation

- `methodology.py` is a pure function of the weights module — no I/O, unit-
  tested in isolation. Keeps `build.py` thin.
- Logo/flag capture is localized: URL constants in `config.py`; club logo in
  `mapping.py`; flag/headshot in `wc_stats.py`. `build.py` only threads values
  through. Each module keeps its single responsibility.
- Frontend gains a small `img`/avatar helper and an explainer renderer; the
  existing safe `el()` builder is reused.

## 6. Error handling

- Any missing asset URL is stored as `None`; the frontend skips or falls back.
- `onerror` on each `<img>` removes the broken image (crest/flag/league) or
  advances the fallback chain (headshot→flag→initials). No broken-image icons.
- The pipeline never fails because a logo is absent; `standings.json` remains
  structurally valid and the fail-soft write rule is unchanged.

## 7. Testing

- **`tests/test_methodology.py`** (new): `build_methodology(weights)` returns the
  four groups, a weights table matching `weights.WEIGHTS`, the four views, and
  notes — pure, no I/O.
- **`tests/test_mapping.py`** (extend): assert `clubLogo` captured from
  `roster.team.logo`.
- **`tests/test_wc_stats.py`** (extend): assert `nationFlag` captured from
  `team.logos` and `headshot` derived from the athlete id.
- **`tests/test_build.py`** (extend): assert club has `clubLogo`/`leagueLogo`,
  player has `nationFlag`/`headshot`, and standings has `methodology`.
- **`tests/test_standings_contract.py`** (extend): new keys present.
- **Frontend:** manual browser check + the existing serve-and-fetch smoke
  (assets 200, page renders logos and the explainer panel toggles).

## 8. Out of scope (YAGNI)

- Bundling/self-hosting image assets (ESPN CDN is sufficient and free).
- Dark-variant flag selection logic (use the default variant; flags carry their
  own colours and read fine on the dark theme).
- Player profile links, club pages, or any navigation beyond the explainer toggle.
- Caching/proxying ESPN images.
