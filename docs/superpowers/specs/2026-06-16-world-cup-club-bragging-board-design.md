# World Cup Club Bragging Board — Design Spec

**Date:** 2026-06-16
**Status:** Approved design, pending spec review
**Project home:** `~/Projects/brag`

## 1. Overview

A live-updating leaderboard that ranks the clubs of Europe's "big five" domestic
leagues by how well *their* players are performing at the FIFA World Cup 2026.
A player's World Cup performance is attributed to the club he played for in the
just-completed domestic season. Purpose: bragging rights — "our club's players
are tearing up the World Cup."

Output is a single static web page, rebuilt on a schedule and served for free.
It is shareable via one URL and updates itself throughout the tournament with no
server to maintain.

## 2. Scope

**In scope**
- Leagues (big five): Premier League (`eng.1`), La Liga (`esp.1`), Serie A
  (`ita.1`), Ligue 1 (`fra.1`), Bundesliga (`ger.1`).
- All clubs in those leagues, attributed via their 2025–26 squads.
- World Cup 2026 men's tournament (`fifa.world`), completed and in-progress
  matches only.
- A per-player, position-aware, stat-derived rating with a visible component
  breakdown.
- Four aggregation views per club: **Total**, **Average per player**,
  **Per-90 (minutes-weighted)**, **Best XI**.
- Two layouts: a combined cross-league table (all clubs ranked together) and
  per-league tabs.

**Out of scope (YAGNI)**
- Women's World Cup, other leagues, lower divisions.
- True real-time (sub-minute) updates — scheduled near-live is sufficient.
- User accounts, betting/odds, historical tournaments, predictions.
- A backend server or database — the artifact is static files.
- Manual editing UI for the mapping or weights (config is code/data files).

## 3. Data source: ESPN unofficial soccer API

No API key, no signup. Base: `https://site.api.espn.com/apis/site/v2/sports/soccer`.
Verified working against live WC 2026 data on 2026-06-16.

### Endpoints used
- **WC fixtures / event IDs:** `…/fifa.world/scoreboard?dates=YYYYMMDD`
  (iterate the tournament date range to collect all event IDs).
- **Per-match player data:** `…/fifa.world/summary?event={id}` — returns:
  - `rosters[].roster[]` — every player with `starter`, `subbedIn`,
    `subbedOut`, `position.abbreviation`, and a `stats[]` array of ~14 fields
    (e.g. `appearances`, `goalAssists`, `shotsOnTarget`, `saves`,
    `goalsConceded`, `shotsFaced`, `foulsCommitted`, `foulsSuffered`,
    `yellowCards`, `redCards`, `ownGoals`, `subIns`). Goals/totalShots/
    accuratePasses/defensiveInterventions appear via `keyEvents`/`leaders`.
  - `keyEvents[]` — timestamped goals, cards, subs with the player named.
  - `leaders[]` — per-category top performers.
- **Domestic squads (for mapping):**
  `…/{leagueCode}/teams` → club list, then
  `…/{leagueCode}/teams/{teamId}/roster?season=2025` → squad with athlete IDs.

### Verified facts (proven 2026-06-16, recorded so we don't re-derive)
- WC per-match `summary` exposes genuine per-player stats + minutes. ✅
- **Athlete IDs are globally consistent** across `fifa.world` and the domestic
  league competitions. Proven: USA WC squad ∩ Serie A rosters by ID →
  McKennie (id 256715) → Juventus, Pulisic (id 225607) → AC Milan. ✅
- **CRITICAL:** domestic `roster` endpoints return **empty** during the summer
  off-season unless a season is pinned. `?season=2025` (the 2025–26 season)
  returned 577 Serie A players; with no season param it returned 0. The
  pipeline MUST pin the just-ended season. Season value is a config constant.

### Caveats (designed around)
- Unofficial/undocumented API — response shape may change mid-tournament.
  Pipeline fails soft (see §9).
- Summer transfer window overlaps the tournament; we deliberately attribute by
  the **just-ended 2025–26 squad**, not live transfer state. This is the correct
  "which league's clubs are bragging" semantic and is stated on the page.

## 4. Player → club mapping (automatic)

Built fresh each run, no hand-curation:
1. For each of the five league codes, fetch `teams`, then each team's
   `roster?season=2025`.
2. Build `athleteId → { club, league, position }`.
3. When processing WC match rosters, look each player up by athlete ID.
4. Players whose national-team WC appearance has no big-five club match are
   simply excluded (e.g., MLS/Saudi/etc. players) — that is correct behaviour.

**Fallback** (only if ID match ever degrades): name + nationality + DOB fuzzy
match. Not expected to be needed given the verification above; implemented only
if a gap is observed. The mapping step logs counts (players mapped vs WC players
seen) so coverage is observable each run.

## 5. Rating methodology (position-aware, transparent)

Each player accumulates stats across all their WC matches, then receives a
single rating computed with **position-group weights** (GK / DEF / MID / FWD,
from `position.abbreviation`). Every player's rating retains its **component
breakdown** (which stat contributed how many points), surfaced on the page so
viewers can see exactly why a number is what it is.

### Weighting framework (starting values — tunable in one config file)
Positive contributions and penalties, applied to per-player accumulated stats.
Exact ESPN field keys are enumerated against the live schema as the first
implementation step (dump all `stats[].name` values), then mapped to these:

| Component | GK | DEF | MID | FWD | Notes |
|---|---|---|---|---|---|
| Goal | +6 | +6 | +5 | +4 | rarer for keepers/def → worth more |
| Assist | +4 | +4 | +4 | +3 | |
| Shot on target | +0.5 | +0.5 | +0.7 | +1 | |
| Save | +1 | — | — | — | |
| Clean sheet (played, 0 conceded) | +4 | +4 | +1 | — | |
| Goal conceded | −1 | −0.5 | — | — | |
| Key defensive intervention | +0.3 | +0.5 | +0.3 | — | |
| Accurate pass (scaled, e.g. /10) | +0.1 | +0.2 | +0.3 | +0.1 | |
| Yellow card | −1 | −1 | −1 | −1 | |
| Red card | −3 | −3 | −3 | −3 | |
| Own goal | −4 | −4 | −4 | −4 | |
| Appearance / minutes baseline | small per-90 floor so featuring counts | | | | |

Weights live in `config/weights.py` (or `.json`) as the single source of truth.
The page links to a short "How scoring works" explainer generated from this
config so the methodology is transparent and arguable.

## 6. Aggregation — four club views

Same per-player ratings, rolled up four ways. All four are computed in the
pipeline and shipped in the data file; the page toggles between them client-side.

- **Total** — sum of every mapped player's rating for the club. Rewards depth +
  quality; big clubs with many internationals climb.
- **Average per player** — mean rating across the club's WC players. Normalizes
  squad size.
- **Per-90** — minutes-weighted: `sum(rating) / (sum(minutes)/90)`. Rewards
  players who actually featured and performed.
- **Best XI** — sum of the club's top 11 player ratings only. Caps the
  big-club advantage while rewarding stars.

Minutes are derived from `starter` + `subbedIn`/`subbedOut` clock values in the
WC `summary` (with `keyEvents` substitution times as the source of truth).

## 7. Architecture

**Compute-once data file + client-rendered views.**

```
                ESPN unofficial API
                       │
        ┌──────────────┴───────────────┐
        │   Python pipeline (no key)    │
        │  1. fetch domestic rosters    │
        │     (season=2025) → mapping   │
        │  2. fetch WC events + summaries│
        │  3. accumulate per-player stats│
        │  4. rate (position-aware)      │
        │  5. aggregate → 4 views/club   │
        └──────────────┬───────────────┘
                       │ writes
                 standings.json  (+ meta: generatedAt, season, coverage)
                       │
        ┌──────────────┴───────────────┐
        │   Static page (HTML + vanilla JS) │
        │  loads standings.json, renders:   │
        │   - combined cross-league table   │
        │   - per-league tabs               │
        │   - view toggle (4 aggregations)  │
        │   - expandable rating breakdowns  │
        └───────────────────────────────────┘
                       ▲
        GitHub Action (cron ~15 min) re-runs pipeline,
        commits standings.json, deploys to GitHub Pages
```

The backend is a dumb, diffable data file. All interactivity (view toggles,
league filtering, breakdown expansion) is client-side — no rebuild needed to
change views. The cron only governs data freshness.

### Components (each independently testable)
- `espn_client.py` — thin HTTP wrapper (fetch + JSON, retries, fail-soft). One
  job: talk to ESPN.
- `mapping.py` — builds `athleteId → club/league/position` from domestic rosters.
- `wc_stats.py` — collects WC events and accumulates per-player stats + minutes.
- `rating.py` — pure functions: stats → rating + breakdown (no I/O; easy to test).
- `aggregate.py` — pure functions: player ratings → four club views.
- `build.py` — orchestrates the above, writes `standings.json`.
- `web/` — `index.html`, `app.js`, `styles.css`; reads `standings.json`.
- `.github/workflows/build.yml` — cron + deploy.

## 8. Page / UX

- **Headline:** combined cross-league table — every club ranked together, league
  badge/colour per row, current view's score, rank, player count.
- **Tabs/filter:** switch to a single league's board.
- **View toggle:** Total / Average / Per-90 / Best XI (re-sorts client-side).
- **Expandable row:** reveals the club's contributing players, each with their
  rating and a component breakdown (e.g. "Pulisic 14.5 = 2 goals +12, 1 assist
  +4, −1.5 …").
- **Footer/meta:** "Updated {generatedAt}", season attribution note, "How
  scoring works" link, data-source credit + unofficial-API disclaimer.
- Mobile-friendly, no framework required. Loads one JSON; everything else is
  client-side.

## 9. Error handling & resilience

- `espn_client` retries transient failures; on hard failure for any single
  endpoint, that match/club is skipped and logged — a partial run still
  produces a valid file.
- **Atomic, fail-soft writes:** `standings.json` is only overwritten if the run
  produced a structurally valid result with non-zero coverage. Otherwise the
  **last good file is kept** and the failure is logged. The page therefore never
  shows an empty/broken board because one cron run hit a hiccup.
- Schema drift guard: pipeline validates expected keys exist before computing;
  if ESPN changes shape, it logs a clear error and keeps the last good file.
- `standings.json` carries `generatedAt`, `season`, `eventsProcessed`, and
  `playersMapped` so staleness/coverage is visible on the page and in logs.

## 10. Data model — `standings.json` (sketch)

```json
{
  "generatedAt": "2026-06-16T18:40:00Z",
  "season": 2025,
  "tournament": "fifa.world",
  "coverage": { "eventsProcessed": 12, "playersMapped": 240 },
  "clubs": [
    {
      "club": "Arsenal", "league": "eng.1", "leagueName": "Premier League",
      "scores": { "total": 88.5, "average": 9.8, "per90": 7.1, "bestXI": 75.0 },
      "playerCount": 9,
      "players": [
        {
          "id": "225607", "name": "Bukayo Saka", "position": "MID",
          "nation": "England", "minutes": 270, "rating": 14.5,
          "breakdown": [
            { "label": "Goals (2)", "points": 10.0 },
            { "label": "Assists (1)", "points": 4.0 },
            { "label": "Yellow card", "points": -1.0 }
          ]
        }
      ]
    }
  ]
}
```

## 11. Testing strategy

- **Pure-function unit tests** for `rating.py` and `aggregate.py` with fixed
  stat inputs → known ratings and known four-view rollups (TDD; these are the
  core logic and have no I/O).
- **Fixture-based tests** for `mapping.py` and `wc_stats.py` using captured
  ESPN JSON responses (committed under `tests/fixtures/`) so tests run offline
  and survive the API going away.
- **Smoke test** (`build.py --dry-run`) that runs end-to-end against live ESPN
  and asserts coverage thresholds (≥N events, ≥M players mapped) — used in CI
  to catch upstream shape changes early.

## 12. Open questions / risks

- **Exact stat field keys:** the precise `stats[].name` set per player is
  enumerated as the first implementation task; §5 weights are mapped to real
  keys then. Low risk — fields observed already, just need the full list.
- **Goals source:** confirm whether a per-player goals field exists in
  `roster[].stats` or must be derived from `keyEvents`. Implementation detail.
- **Season constant:** `2025` confirmed populated today; revisit if ESPN rolls
  the season label during the tournament.
- **Cron granularity:** GitHub Actions cron min interval is ~5 min and not
  guaranteed exact; ~15 min target is fine for "near-live."

## 13. Tech stack

- Pipeline: **Python 3**, standard library only where practical (`urllib`,
  `json`); optional tiny templating for the explainer page. No API key, no DB.
- Frontend: plain **HTML + vanilla JS + CSS**, single `standings.json` fetch.
- Schedule/hosting: **GitHub Actions** (cron) + **GitHub Pages**. Fully free.
