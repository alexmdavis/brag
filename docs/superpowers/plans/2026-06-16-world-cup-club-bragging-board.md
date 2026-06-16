# World Cup Club Bragging Board — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A static, auto-rebuilt web leaderboard ranking big-five-league clubs by their players' FIFA World Cup 2026 performance.

**Architecture:** A Python pipeline (stdlib only) fetches the ESPN unofficial API, maps each WC player to his 2025–26 domestic club via globally-consistent athlete IDs, computes a position-aware per-player rating with a component breakdown, aggregates four club views (Total / Average / Per-90 / Best XI), and writes one `standings.json`. A static HTML+JS page renders all views client-side. A GitHub Action rebuilds on a cron and deploys to GitHub Pages.

**Tech Stack:** Python 3 (stdlib `urllib`, `json`), pytest for tests, vanilla HTML/CSS/JS, GitHub Actions + Pages.

---

## Verified facts (do not re-derive — proven against live API 2026-06-16)

- Base URL: `https://site.api.espn.com/apis/site/v2/sports/soccer`. No API key.
- WC league code `fifa.world`. Domestic codes: `eng.1`, `esp.1`, `ita.1`, `fra.1`, `ger.1`.
- Athlete IDs are **globally consistent** across `fifa.world` and domestic competitions (proven: McKennie 256715→Juventus, Pulisic 225607→AC Milan).
- **Domestic roster endpoints return empty unless `?season=2025` is passed** (off-season). This is mandatory.
- WC per-match data: `GET …/fifa.world/summary?event={id}` →
  - `rosters[]` (2 teams) → `team.displayName`, `roster[]` with keys `athlete.{id,displayName}`, `starter` (bool), `subbedIn` (bool), `subbedOut` (bool), `position.{abbreviation,name}` (tactical; subs show `SUB`), and `stats[]`.
  - Per-player `stats[]` field names (15): `appearances`, `foulsCommitted`, `foulsSuffered`, `goalAssists`, `goalsConceded`, `offsides`, `ownGoals`, `redCards`, `saves`, `shotsFaced`, `shotsOnTarget`, `subIns`, `totalGoals`, `totalShots`, `yellowCards`. (`accuratePasses`/`defensiveInterventions` are NOT per-player — only in `leaders` — so they are excluded.)
  - `keyEvents[]` → `type.text` (e.g. `Substitution`, `Goal`, `Yellow Card`), `clock.displayValue` (e.g. `61'`), `participants[].athlete.id`.
  - `header.competitions[0].competitors[]` → `team.id`, `score` (string), `homeAway` — used for clean-sheet (team goals conceded).
- WC fixtures: `GET …/fifa.world/scoreboard?dates=YYYYMMDD` → `events[]` with `id`, `status.type.completed` (bool), `status.type.state`.
- Domestic squads: `GET …/{league}/teams` → `sports[0].leagues[0].teams[].team.{id,displayName}`; then `GET …/{league}/teams/{teamId}/roster?season=2025` → `team.displayName`, `athletes[]` with `id`, `displayName`, `position.abbreviation` in **{G, D, M, F}**.

---

## File structure

```
~/Projects/brag/
├── src/
│   ├── __init__.py
│   ├── config.py        # leagues, season, base URL, tournament dates
│   ├── weights.py       # position-aware rating weights (single source of truth)
│   ├── espn_client.py   # HTTP wrapper: fetch_json with retries (injectable opener)
│   ├── rating.py        # PURE: position_group(), rate_player()
│   ├── aggregate.py     # PURE: aggregate_club() -> 4 views
│   ├── minutes.py       # PURE: parse_minute, parse_sub_events, compute_minutes
│   ├── mapping.py       # build_mapping() athleteId -> club/league/position
│   ├── wc_stats.py      # accumulate_players(): WC events -> per-player records
│   └── build.py         # orchestrate -> web/standings.json (atomic, fail-soft)
├── web/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── standings.json   # generated artifact (committed by the Action)
├── tests/
│   ├── fixtures/        # captured real ESPN JSON (offline tests)
│   ├── test_rating.py
│   ├── test_aggregate.py
│   ├── test_minutes.py
│   ├── test_espn_client.py
│   ├── test_mapping.py
│   ├── test_wc_stats.py
│   ├── test_build.py
│   └── test_standings_contract.py
├── .github/workflows/build.yml
├── requirements-dev.txt
└── README.md
```

Run all tests from repo root with `python3 -m pytest -q`.

---

### Task 1: Scaffold, config, weights

**Files:**
- Create: `src/__init__.py` (empty), `src/config.py`, `src/weights.py`
- Create: `requirements-dev.txt`, `tests/__init__.py` (empty)
- Test: `tests/test_config.py`

- [ ] **Step 1: Create dev requirements and empty package files**

`requirements-dev.txt`:
```
pytest>=8
```

Create empty `src/__init__.py` and `tests/__init__.py`.

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
from src import config, weights


def test_five_leagues_with_names():
    assert set(config.LEAGUES) == {"eng.1", "esp.1", "ita.1", "fra.1", "ger.1"}
    assert config.LEAGUES["eng.1"] == "Premier League"


def test_season_is_pinned_int():
    assert config.SEASON == 2025  # 2025-26; rosters are empty without it


def test_base_and_tournament():
    assert config.BASE.endswith("/sports/soccer")
    assert config.WC_LEAGUE == "fifa.world"
    assert config.TOURNAMENT_START == "20260611"
    assert config.TOURNAMENT_END == "20260719"


def test_weights_cover_four_groups():
    assert set(weights.WEIGHTS) == {"GK", "DEF", "MID", "FWD"}
    assert set(weights.POSITION_GROUPS) == {"G", "D", "M", "F"}
    assert set(weights.CLEAN_SHEET_BONUS) == {"GK", "DEF", "MID", "FWD"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: FAIL (`ModuleNotFoundError: src.config`).

- [ ] **Step 4: Implement config and weights**

`src/config.py`:
```python
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
WC_LEAGUE = "fifa.world"
SEASON = 2025  # 2025-26 season; domestic roster endpoints return empty without this

LEAGUES = {
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "ger.1": "Bundesliga",
}

# Inclusive YYYYMMDD range to scan the WC scoreboard for event IDs.
TOURNAMENT_START = "20260611"
TOURNAMENT_END = "20260719"
```

`src/weights.py`:
```python
# Map ESPN domestic-roster position abbreviation -> rating group.
POSITION_GROUPS = {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"}

# Points per unit of each accumulated WC stat field, by position group.
# Field names are the exact ESPN per-player stat names.
WEIGHTS = {
    "GK": {
        "totalGoals": 6.0, "goalAssists": 4.0, "shotsOnTarget": 0.5,
        "saves": 1.0, "goalsConceded": -1.0,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
        "foulsCommitted": -0.1,
    },
    "DEF": {
        "totalGoals": 6.0, "goalAssists": 4.0, "shotsOnTarget": 0.5,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
        "foulsCommitted": -0.1,
    },
    "MID": {
        "totalGoals": 5.0, "goalAssists": 4.0, "shotsOnTarget": 0.7,
        "totalShots": 0.1,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
        "foulsCommitted": -0.1,
    },
    "FWD": {
        "totalGoals": 4.0, "goalAssists": 3.0, "shotsOnTarget": 1.0,
        "totalShots": 0.2,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
    },
}

# Bonus per clean sheet (a match the player featured in where his team conceded 0).
CLEAN_SHEET_BONUS = {"GK": 4.0, "DEF": 4.0, "MID": 1.0, "FWD": 0.0}

# Small floor so simply featuring counts for something.
APPEARANCE_POINTS = 0.5

# Human-readable labels for breakdown components.
FIELD_LABELS = {
    "totalGoals": "Goals", "goalAssists": "Assists", "shotsOnTarget": "Shots on target",
    "totalShots": "Shots", "saves": "Saves", "goalsConceded": "Goals conceded",
    "yellowCards": "Yellow cards", "redCards": "Red cards", "ownGoals": "Own goals",
    "foulsCommitted": "Fouls committed",
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add src/__init__.py src/config.py src/weights.py tests/__init__.py tests/test_config.py requirements-dev.txt
git commit -m "feat: project scaffold, config and rating weights"
```

---

### Task 2: Rating (pure)

**Files:**
- Create: `src/rating.py`
- Test: `tests/test_rating.py`

`rate_player` consumes one accumulated record and returns `{"rating": float, "breakdown": [{"label": str, "points": float}]}`. Breakdown lists only non-zero components. `rating` is the rounded sum.

- [ ] **Step 1: Write the failing test**

`tests/test_rating.py`:
```python
from src.rating import position_group, rate_player


def test_position_group_known_and_default():
    assert position_group("G") == "GK"
    assert position_group("D") == "DEF"
    assert position_group("M") == "MID"
    assert position_group("F") == "FWD"
    assert position_group("SUB") == "MID"   # unknown -> default
    assert position_group(None) == "MID"


def _record(position, stats, clean_sheets=0):
    return {"position": position, "stats": stats, "cleanSheets": clean_sheets}


def test_forward_goals_and_assists():
    rec = _record("F", {"totalGoals": 2, "goalAssists": 1, "shotsOnTarget": 3,
                         "appearances": 2})
    out = rate_player(rec)
    # 2*4 + 1*3 + 3*1.0 + 2*0.5 appearance floor = 8 + 3 + 3 + 1 = 15.0
    assert out["rating"] == 15.0
    labels = {c["label"]: c["points"] for c in out["breakdown"]}
    assert labels["Goals"] == 8.0
    assert labels["Assists"] == 3.0
    assert labels["Appearances"] == 1.0


def test_keeper_saves_clean_sheet_and_concede():
    rec = _record("G", {"saves": 4, "goalsConceded": 1, "appearances": 2},
                  clean_sheets=1)
    out = rate_player(rec)
    # 4*1 saves + (-1)*1 conceded + 1*4 clean sheet + 2*0.5 appearances = 4 -1 +4 +1 = 8.0
    assert out["rating"] == 8.0
    labels = {c["label"]: c["points"] for c in out["breakdown"]}
    assert labels["Saves"] == 4.0
    assert labels["Goals conceded"] == -1.0
    assert labels["Clean sheets"] == 4.0


def test_zero_components_excluded_from_breakdown():
    rec = _record("M", {"totalGoals": 0, "goalAssists": 1, "appearances": 1})
    out = rate_player(rec)
    labels = [c["label"] for c in out["breakdown"]]
    assert "Goals" not in labels       # zero contribution dropped
    assert "Assists" in labels


def test_cards_are_penalties():
    rec = _record("D", {"yellowCards": 1, "redCards": 1, "appearances": 1})
    out = rate_player(rec)
    # -1 -3 + 0.5 appearance = -3.5
    assert out["rating"] == -3.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_rating.py -q`
Expected: FAIL (`ModuleNotFoundError: src.rating`).

- [ ] **Step 3: Implement `src/rating.py`**

```python
from src.weights import (
    POSITION_GROUPS, WEIGHTS, CLEAN_SHEET_BONUS, APPEARANCE_POINTS, FIELD_LABELS,
)


def position_group(abbreviation):
    """Map a domestic-roster position abbreviation to a rating group."""
    return POSITION_GROUPS.get(abbreviation, "MID")


def rate_player(record):
    """record: {"position": str, "stats": {field: number}, "cleanSheets": int}

    Returns {"rating": float, "breakdown": [{"label": str, "points": float}]}.
    """
    group = position_group(record.get("position"))
    stats = record.get("stats", {})
    components = []

    for field, weight in WEIGHTS[group].items():
        value = stats.get(field, 0) or 0
        points = round(value * weight, 2)
        if points != 0:
            components.append({"label": FIELD_LABELS.get(field, field), "points": points})

    clean_sheets = record.get("cleanSheets", 0) or 0
    cs_points = round(clean_sheets * CLEAN_SHEET_BONUS[group], 2)
    if cs_points != 0:
        components.append({"label": "Clean sheets", "points": cs_points})

    appearances = stats.get("appearances", 0) or 0
    app_points = round(appearances * APPEARANCE_POINTS, 2)
    if app_points != 0:
        components.append({"label": "Appearances", "points": app_points})

    rating = round(sum(c["points"] for c in components), 2)
    return {"rating": rating, "breakdown": components}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_rating.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/rating.py tests/test_rating.py
git commit -m "feat: position-aware per-player rating with breakdown"
```

---

### Task 3: Aggregate (pure)

**Files:**
- Create: `src/aggregate.py`
- Test: `tests/test_aggregate.py`

`aggregate_club(players)` where each player is `{"rating": float, "minutes": int}`. Returns `{"total","average","per90","bestXI"}`, each rounded to 2 dp.

- [ ] **Step 1: Write the failing test**

`tests/test_aggregate.py`:
```python
from src.aggregate import aggregate_club


def test_four_views():
    players = [
        {"rating": 10.0, "minutes": 90},
        {"rating": 6.0, "minutes": 45},
        {"rating": 2.0, "minutes": 90},
    ]
    s = aggregate_club(players)
    assert s["total"] == 18.0
    assert s["average"] == 6.0                      # 18 / 3
    # per90 = 18 / (225/90) = 18 / 2.5 = 7.2
    assert s["per90"] == 7.2
    assert s["bestXI"] == 18.0                       # fewer than 11 -> all


def test_best_xi_caps_at_eleven():
    players = [{"rating": float(i), "minutes": 90} for i in range(1, 14)]  # 1..13
    s = aggregate_club(players)
    # top 11 of 1..13 = 3..13 sum = (3+13)*11/2 = 88
    assert s["bestXI"] == 88.0
    assert s["total"] == 91.0                        # 1..13 sum


def test_empty_club_is_zeroed():
    s = aggregate_club([])
    assert s == {"total": 0.0, "average": 0.0, "per90": 0.0, "bestXI": 0.0}


def test_per90_zero_when_no_minutes():
    s = aggregate_club([{"rating": 5.0, "minutes": 0}])
    assert s["per90"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_aggregate.py -q`
Expected: FAIL (`ModuleNotFoundError: src.aggregate`).

- [ ] **Step 3: Implement `src/aggregate.py`**

```python
def aggregate_club(players):
    """players: list of {"rating": float, "minutes": int}.

    Returns the four club views, each rounded to 2 dp.
    """
    if not players:
        return {"total": 0.0, "average": 0.0, "per90": 0.0, "bestXI": 0.0}

    ratings = [p["rating"] for p in players]
    total = sum(ratings)
    total_minutes = sum(p.get("minutes", 0) for p in players)

    average = total / len(players)
    per90 = (total / (total_minutes / 90)) if total_minutes > 0 else 0.0
    best_xi = sum(sorted(ratings, reverse=True)[:11])

    return {
        "total": round(total, 2),
        "average": round(average, 2),
        "per90": round(per90, 2),
        "bestXI": round(best_xi, 2),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_aggregate.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aggregate.py tests/test_aggregate.py
git commit -m "feat: four-view club aggregation"
```

---

### Task 4: Minutes (pure)

**Files:**
- Create: `src/minutes.py`
- Test: `tests/test_minutes.py`

Derive minutes from the WC roster booleans + `Substitution` key events. A player is matched to a sub event when his athlete id appears in that event's participants; direction comes from his own `subbedIn`/`subbedOut` flags.

- [ ] **Step 1: Write the failing test**

`tests/test_minutes.py`:
```python
from src.minutes import parse_minute, parse_sub_events, compute_minutes


def test_parse_minute():
    assert parse_minute("61'") == 61
    assert parse_minute("45'+2") == 45
    assert parse_minute("90'+4") == 90
    assert parse_minute("") == 0


def test_parse_sub_events():
    key_events = [
        {"type": {"text": "Substitution"}, "clock": {"displayValue": "61'"},
         "participants": [{"athlete": {"id": "1"}}, {"athlete": {"id": "2"}}]},
        {"type": {"text": "Goal"}, "clock": {"displayValue": "70'"},
         "participants": [{"athlete": {"id": "3"}}]},
    ]
    subs = parse_sub_events(key_events)
    assert subs == [{"minute": 61, "ids": {"1", "2"}}]


SUBS = [{"minute": 61, "ids": {"10", "20"}}]


def test_starter_full_match():
    p = {"athlete": {"id": "99"}, "starter": True, "subbedIn": False, "subbedOut": False}
    assert compute_minutes(p, SUBS) == 90


def test_starter_subbed_out():
    p = {"athlete": {"id": "10"}, "starter": True, "subbedIn": False, "subbedOut": True}
    assert compute_minutes(p, SUBS) == 61


def test_sub_came_on():
    p = {"athlete": {"id": "20"}, "starter": False, "subbedIn": True, "subbedOut": False}
    assert compute_minutes(p, SUBS) == 29   # 90 - 61


def test_unused_player_zero():
    p = {"athlete": {"id": "77"}, "starter": False, "subbedIn": False, "subbedOut": False}
    assert compute_minutes(p, SUBS) == 0


def test_subbed_out_without_event_defaults_full():
    p = {"athlete": {"id": "55"}, "starter": True, "subbedIn": False, "subbedOut": True}
    assert compute_minutes(p, []) == 90
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_minutes.py -q`
Expected: FAIL (`ModuleNotFoundError: src.minutes`).

- [ ] **Step 3: Implement `src/minutes.py`**

```python
import re


def parse_minute(clock_display):
    """'61\\'' -> 61, '45\\'+2' -> 45, '' -> 0."""
    if not clock_display:
        return 0
    m = re.match(r"\s*(\d+)", clock_display)
    minute = int(m.group(1)) if m else 0
    return min(minute, 90)


def parse_sub_events(key_events):
    """Return [{'minute': int, 'ids': set(athlete_id)}] for Substitution events."""
    out = []
    for e in key_events or []:
        if (e.get("type", {}) or {}).get("text") != "Substitution":
            continue
        minute = parse_minute((e.get("clock", {}) or {}).get("displayValue"))
        ids = {
            (p.get("athlete", {}) or {}).get("id")
            for p in e.get("participants", []) or []
            if (p.get("athlete", {}) or {}).get("id")
        }
        out.append({"minute": minute, "ids": ids})
    return out


def _sub_minute_for(player_id, sub_events):
    for s in sub_events:
        if player_id in s["ids"]:
            return s["minute"]
    return None


def compute_minutes(player, sub_events):
    """Minutes in [0, 90] from roster booleans + matched Substitution events."""
    pid = (player.get("athlete", {}) or {}).get("id")
    starter = bool(player.get("starter"))
    subbed_in = bool(player.get("subbedIn"))
    subbed_out = bool(player.get("subbedOut"))
    minute = _sub_minute_for(pid, sub_events)

    if starter and not subbed_out:
        return 90
    if starter and subbed_out:
        return minute if minute is not None else 90
    if subbed_in:
        return max(1, 90 - minute) if minute is not None else 15
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_minutes.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/minutes.py tests/test_minutes.py
git commit -m "feat: derive player minutes from substitution events"
```

---

### Task 5: ESPN client

**Files:**
- Create: `src/espn_client.py`
- Test: `tests/test_espn_client.py`

`fetch_json(url, opener=None, retries=3)` returns parsed JSON, retrying transient failures. `opener` is injectable for tests (a callable `url -> file-like with .read()`).

- [ ] **Step 1: Write the failing test**

`tests/test_espn_client.py`:
```python
import io
import json
import pytest
from src.espn_client import fetch_json


def make_opener(payloads):
    """payloads: list of either bytes (success) or Exception (raise)."""
    calls = {"n": 0}

    def opener(request, timeout=0):
        i = calls["n"]
        calls["n"] += 1
        item = payloads[min(i, len(payloads) - 1)]
        if isinstance(item, Exception):
            raise item
        return io.BytesIO(item)

    return opener, calls


def test_returns_parsed_json():
    opener, _ = make_opener([json.dumps({"ok": 1}).encode()])
    assert fetch_json("http://x", opener=opener) == {"ok": 1}


def test_retries_then_succeeds():
    opener, calls = make_opener([OSError("flaky"), json.dumps({"ok": 2}).encode()])
    assert fetch_json("http://x", opener=opener, retries=3) == {"ok": 2}
    assert calls["n"] == 2


def test_raises_after_exhausting_retries():
    opener, _ = make_opener([OSError("down")])
    with pytest.raises(OSError):
        fetch_json("http://x", opener=opener, retries=2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_espn_client.py -q`
Expected: FAIL (`ModuleNotFoundError: src.espn_client`).

- [ ] **Step 3: Implement `src/espn_client.py`**

```python
import json
import urllib.request

_HEADERS = {"User-Agent": "Mozilla/5.0 (brag-board)"}


def _default_opener(request, timeout=30):
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_json(url, opener=None, retries=3, timeout=30):
    """Fetch and parse JSON. Retries transient errors; raises the last error."""
    opener = opener or _default_opener
    request = urllib.request.Request(url, headers=_HEADERS)
    last = None
    for _ in range(max(1, retries)):
        try:
            with opener(request, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last = exc
    raise last
```

Note: the test's fake opener returns a `BytesIO` (a context manager), matching the `with opener(...) as resp` usage.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_espn_client.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/espn_client.py tests/test_espn_client.py
git commit -m "feat: ESPN HTTP client with retries and injectable opener"
```

---

### Task 6: Mapping (athlete id -> club/league/position)

**Files:**
- Create: `src/mapping.py`
- Test: `tests/test_mapping.py`

`build_mapping(fetch)` iterates `config.LEAGUES`, fetches each league's `teams`, then each team's `roster?season=SEASON`, returning `{athleteId: {"club","league","leagueName","position"}}`. `fetch` is injected (defaults to `fetch_json`). URLs are built from `config.BASE`.

- [ ] **Step 1: Write the failing test**

`tests/test_mapping.py`:
```python
from src import config
from src.mapping import build_mapping, teams_url, roster_url


def test_url_builders():
    assert teams_url("ita.1") == f"{config.BASE}/ita.1/teams"
    assert roster_url("ita.1", "103") == f"{config.BASE}/ita.1/teams/103/roster?season={config.SEASON}"


def fake_fetch_factory():
    teams_payload = {"sports": [{"leagues": [{"teams": [
        {"team": {"id": "103", "displayName": "AC Milan"}},
    ]}]}]}
    roster_payload = {"team": {"displayName": "AC Milan"}, "athletes": [
        {"id": "225607", "displayName": "Christian Pulisic", "position": {"abbreviation": "M"}},
        {"id": "236210", "displayName": "Fikayo Tomori", "position": {"abbreviation": "D"}},
    ]}

    def fetch(url, **kwargs):
        if url.endswith("/teams"):
            return teams_payload
        if "/roster" in url:
            return roster_payload
        raise AssertionError(f"unexpected url {url}")
    return fetch


def test_build_mapping_indexes_by_athlete_id():
    # Restrict to one league for the test.
    m = build_mapping(fetch=fake_fetch_factory(), leagues={"ita.1": "Serie A"})
    assert m["225607"] == {
        "club": "AC Milan", "league": "ita.1",
        "leagueName": "Serie A", "position": "M",
    }
    assert m["236210"]["position"] == "D"


def test_build_mapping_skips_failed_team(monkeypatch):
    def fetch(url, **kwargs):
        if url.endswith("/teams"):
            return {"sports": [{"leagues": [{"teams": [
                {"team": {"id": "1", "displayName": "Good"}},
                {"team": {"id": "2", "displayName": "Bad"}},
            ]}]}]}
        if "/teams/2/roster" in url:
            raise OSError("boom")
        return {"team": {"displayName": "Good"}, "athletes": [
            {"id": "11", "displayName": "A", "position": {"abbreviation": "F"}}]}
    m = build_mapping(fetch=fetch, leagues={"eng.1": "Premier League"})
    assert "11" in m            # good club mapped
    assert len(m) == 1          # bad club skipped, no crash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_mapping.py -q`
Expected: FAIL (`ModuleNotFoundError: src.mapping`).

- [ ] **Step 3: Implement `src/mapping.py`**

```python
from src import config
from src.espn_client import fetch_json


def teams_url(league):
    return f"{config.BASE}/{league}/teams"


def roster_url(league, team_id):
    return f"{config.BASE}/{league}/teams/{team_id}/roster?season={config.SEASON}"


def _league_teams(payload):
    return payload["sports"][0]["leagues"][0]["teams"]


def build_mapping(fetch=fetch_json, leagues=None):
    """Return {athleteId: {club, league, leagueName, position}}.

    Skips any club whose roster fetch fails (fail-soft).
    """
    leagues = leagues if leagues is not None else config.LEAGUES
    mapping = {}
    for league, league_name in leagues.items():
        try:
            teams = _league_teams(fetch(teams_url(league)))
        except Exception:
            continue
        for entry in teams:
            team_id = entry["team"]["id"]
            try:
                roster = fetch(roster_url(league, team_id))
            except Exception:
                continue
            club = roster.get("team", {}).get("displayName") or entry["team"].get("displayName")
            for ath in roster.get("athletes", []):
                aid = ath.get("id")
                if not aid:
                    continue
                mapping[aid] = {
                    "club": club,
                    "league": league,
                    "leagueName": league_name,
                    "position": (ath.get("position", {}) or {}).get("abbreviation"),
                }
    return mapping
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_mapping.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mapping.py tests/test_mapping.py
git commit -m "feat: build athlete-id to club mapping from domestic rosters"
```

---

### Task 7: WC stats accumulation

**Files:**
- Create: `src/wc_stats.py`
- Test: `tests/test_wc_stats.py`

Two functions:
- `process_match_summary(summary, mapping, acc)` — PURE given a parsed summary: for each mapped, featured player, accumulate summed stats, minutes, matches, and clean sheets (team conceded 0 that match).
- `accumulate_players(mapping, fetch)` — collect WC event IDs across the date range, fetch each summary, and fold via `process_match_summary`.

- [ ] **Step 1: Write the failing test**

`tests/test_wc_stats.py`:
```python
from src.wc_stats import process_match_summary, team_goals_conceded


SUMMARY = {
    "header": {"competitions": [{"competitors": [
        {"team": {"id": "T1"}, "homeAway": "home", "score": "2"},
        {"team": {"id": "T2"}, "homeAway": "away", "score": "0"},
    ]}]},
    "keyEvents": [
        {"type": {"text": "Substitution"}, "clock": {"displayValue": "70'"},
         "participants": [{"athlete": {"id": "A2"}}, {"athlete": {"id": "A3"}}]},
    ],
    "rosters": [
        {"team": {"id": "T1", "displayName": "England"}, "roster": [
            {"athlete": {"id": "A1", "displayName": "Saka"}, "starter": True,
             "subbedIn": False, "subbedOut": False,
             "stats": [{"name": "totalGoals", "value": 1.0},
                       {"name": "goalAssists", "value": 0.0},
                       {"name": "appearances", "value": 1.0},
                       {"name": "goalsConceded", "value": 0.0}]},
            {"athlete": {"id": "A2", "displayName": "Bench"}, "starter": False,
             "subbedIn": True, "subbedOut": False,
             "stats": [{"name": "totalGoals", "value": 0.0},
                       {"name": "appearances", "value": 1.0}]},
            {"athlete": {"id": "AX", "displayName": "Unused"}, "starter": False,
             "subbedIn": False, "subbedOut": False, "stats": []},
        ]},
        {"team": {"id": "T2", "displayName": "France"}, "roster": [
            {"athlete": {"id": "U1", "displayName": "Unmapped"}, "starter": True,
             "subbedIn": False, "subbedOut": False, "stats": []},
        ]},
    ],
}

MAPPING = {
    "A1": {"club": "Arsenal", "league": "eng.1", "leagueName": "Premier League", "position": "M"},
    "A2": {"club": "Chelsea", "league": "eng.1", "leagueName": "Premier League", "position": "F"},
    "AX": {"club": "Arsenal", "league": "eng.1", "leagueName": "Premier League", "position": "D"},
    # U1 deliberately absent -> excluded
}


def test_team_goals_conceded():
    assert team_goals_conceded(SUMMARY) == {"T1": 0, "T2": 2}


def test_process_accumulates_featured_mapped_players_only():
    acc = {}
    process_match_summary(SUMMARY, MAPPING, acc)
    # U1 unmapped -> excluded; AX mapped but did not feature -> excluded.
    assert set(acc) == {"A1", "A2"}

    a1 = acc["A1"]
    assert a1["club"] == "Arsenal"
    assert a1["nation"] == "England"
    assert a1["position"] == "M"
    assert a1["stats"]["totalGoals"] == 1.0
    assert a1["minutes"] == 90
    assert a1["matches"] == 1
    assert a1["cleanSheets"] == 1          # T1 conceded 0, A1 featured

    a2 = acc["A2"]
    assert a2["minutes"] == 20             # came on at 70'
    assert a2["cleanSheets"] == 1


def test_process_is_additive_across_matches():
    acc = {}
    process_match_summary(SUMMARY, MAPPING, acc)
    process_match_summary(SUMMARY, MAPPING, acc)
    assert acc["A1"]["stats"]["totalGoals"] == 2.0
    assert acc["A1"]["matches"] == 2
    assert acc["A1"]["minutes"] == 180
    assert acc["A1"]["cleanSheets"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wc_stats.py -q`
Expected: FAIL (`ModuleNotFoundError: src.wc_stats`).

- [ ] **Step 3: Implement `src/wc_stats.py`**

```python
from datetime import date, timedelta

from src import config
from src.espn_client import fetch_json
from src.minutes import parse_sub_events, compute_minutes


def team_goals_conceded(summary):
    """Map team id -> goals conceded (the other competitor's score)."""
    comps = (summary.get("header", {}).get("competitions") or [{}])[0]
    competitors = comps.get("competitors", []) or []
    scores = {}
    for c in competitors:
        tid = (c.get("team", {}) or {}).get("id")
        try:
            scores[tid] = int(c.get("score"))
        except (TypeError, ValueError):
            scores[tid] = 0
    conceded = {}
    total = sum(scores.values())
    for tid, scored in scores.items():
        conceded[tid] = total - scored
    return conceded


def _stats_dict(player):
    return {s.get("name"): (s.get("value") or 0) for s in player.get("stats", []) or []}


def _new_record(pid, player, info, nation):
    return {
        "id": pid,
        "name": player.get("athlete", {}).get("displayName"),
        "nation": nation,
        "club": info["club"],
        "league": info["league"],
        "leagueName": info["leagueName"],
        "position": info["position"],
        "stats": {},
        "minutes": 0,
        "matches": 0,
        "cleanSheets": 0,
    }


def process_match_summary(summary, mapping, acc):
    """Fold one parsed WC match summary into the accumulator `acc` (in place)."""
    subs = parse_sub_events(summary.get("keyEvents"))
    conceded = team_goals_conceded(summary)

    for team in summary.get("rosters", []) or []:
        nation = team.get("team", {}).get("displayName")
        team_id = team.get("team", {}).get("id")
        for player in team.get("roster", []) or []:
            pid = (player.get("athlete", {}) or {}).get("id")
            info = mapping.get(pid)
            if not info:
                continue
            featured = bool(player.get("starter")) or bool(player.get("subbedIn"))
            if not featured:
                continue

            rec = acc.get(pid) or _new_record(pid, player, info, nation)
            match_stats = _stats_dict(player)
            for name, value in match_stats.items():
                rec["stats"][name] = rec["stats"].get(name, 0) + value

            minutes = compute_minutes(player, subs)
            rec["minutes"] += minutes
            rec["matches"] += 1
            if conceded.get(team_id, 1) == 0:
                rec["cleanSheets"] += 1
            acc[pid] = rec


def _date_range(start, end):
    d0 = date(int(start[:4]), int(start[4:6]), int(start[6:8]))
    d1 = date(int(end[:4]), int(end[4:6]), int(end[6:8]))
    days = []
    d = d0
    while d <= d1:
        days.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return days


def collect_event_ids(fetch=fetch_json):
    """Completed or in-progress WC event IDs across the tournament date range."""
    ids = []
    for ymd in _date_range(config.TOURNAMENT_START, config.TOURNAMENT_END):
        url = f"{config.BASE}/{config.WC_LEAGUE}/scoreboard?dates={ymd}"
        try:
            board = fetch(url)
        except Exception:
            continue
        for e in board.get("events", []) or []:
            state = (e.get("status", {}).get("type", {}) or {}).get("state")
            if state in ("post", "in"):     # completed or live; skip "pre"
                ids.append(e.get("id"))
    return ids


def accumulate_players(mapping, fetch=fetch_json):
    """Return {athleteId: record} across all played WC matches."""
    acc = {}
    for eid in collect_event_ids(fetch=fetch):
        url = f"{config.BASE}/{config.WC_LEAGUE}/summary?event={eid}"
        try:
            summary = fetch(url)
        except Exception:
            continue
        process_match_summary(summary, mapping, acc)
    return acc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_wc_stats.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wc_stats.py tests/test_wc_stats.py
git commit -m "feat: accumulate per-player WC stats, minutes and clean sheets"
```

---

### Task 8: Build orchestration (standings.json, fail-soft)

**Files:**
- Create: `src/build.py`
- Test: `tests/test_build.py`

- `assemble_standings(records, rate, aggregate, generated_at)` — PURE: rate every player, group by club, aggregate four views, sort players by rating desc, return the full standings dict (schema per spec §10).
- `write_standings(standings, path)` — atomic write, but only if `coverage.playersMapped > 0`; otherwise keep the existing file (fail-soft) and return `False`.
- `main()` — wire mapping + accumulation + assemble + write; stamp `generatedAt` (passed in, since `datetime.now` is fine in app code but injected here for testability).

- [ ] **Step 1: Write the failing test**

`tests/test_build.py`:
```python
import json
from src.build import assemble_standings, write_standings


RECORDS = {
    "A1": {"id": "A1", "name": "Saka", "nation": "England", "club": "Arsenal",
           "league": "eng.1", "leagueName": "Premier League", "position": "M",
           "stats": {"totalGoals": 2.0, "goalAssists": 1.0, "appearances": 2.0},
           "minutes": 180, "matches": 2, "cleanSheets": 0},
    "A2": {"id": "A2", "name": "Saliba", "nation": "France", "club": "Arsenal",
           "league": "eng.1", "leagueName": "Premier League", "position": "D",
           "stats": {"appearances": 1.0}, "minutes": 90, "matches": 1, "cleanSheets": 1},
}


def test_assemble_groups_and_sorts():
    s = assemble_standings(RECORDS, generated_at="2026-06-16T18:00:00Z")
    assert s["generatedAt"] == "2026-06-16T18:00:00Z"
    assert s["season"] == 2025
    assert s["coverage"]["playersMapped"] == 2
    assert len(s["clubs"]) == 1
    club = s["clubs"][0]
    assert club["club"] == "Arsenal"
    assert club["playerCount"] == 2
    assert set(club["scores"]) == {"total", "average", "per90", "bestXI"}
    # players sorted by rating desc
    ratings = [p["rating"] for p in club["players"]]
    assert ratings == sorted(ratings, reverse=True)
    assert club["players"][0]["name"] == "Saka"
    assert "breakdown" in club["players"][0]


def test_clubs_sorted_by_total_desc():
    recs = dict(RECORDS)
    recs["B1"] = {"id": "B1", "name": "X", "nation": "Spain", "club": "Brighton",
                  "league": "eng.1", "leagueName": "Premier League", "position": "F",
                  "stats": {"appearances": 1.0}, "minutes": 90, "matches": 1, "cleanSheets": 0}
    s = assemble_standings(recs, generated_at="t")
    totals = [c["scores"]["total"] for c in s["clubs"]]
    assert totals == sorted(totals, reverse=True)


def test_write_is_failsoft_on_empty(tmp_path):
    path = tmp_path / "standings.json"
    good = assemble_standings(RECORDS, generated_at="t1")
    assert write_standings(good, str(path)) is True
    assert path.exists()

    empty = assemble_standings({}, generated_at="t2")
    assert write_standings(empty, str(path)) is False     # refused
    on_disk = json.loads(path.read_text())
    assert on_disk["generatedAt"] == "t1"                  # last good kept
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build.py -q`
Expected: FAIL (`ModuleNotFoundError: src.build`).

- [ ] **Step 3: Implement `src/build.py`**

```python
import json
import os
from datetime import datetime, timezone

from src import config
from src.rating import rate_player
from src.aggregate import aggregate_club
from src.mapping import build_mapping
from src.wc_stats import accumulate_players

DEFAULT_OUTPUT = os.path.join("web", "standings.json")


def assemble_standings(records, generated_at):
    """Build the full standings dict from accumulated player records."""
    clubs = {}
    for rec in records.values():
        rated = rate_player(rec)
        player = {
            "id": rec["id"], "name": rec["name"], "position": rec["position"],
            "nation": rec["nation"], "minutes": rec["minutes"],
            "rating": rated["rating"], "breakdown": rated["breakdown"],
        }
        club = clubs.setdefault(rec["club"], {
            "club": rec["club"], "league": rec["league"],
            "leagueName": rec["leagueName"], "players": [],
        })
        club["players"].append(player)

    club_list = []
    for club in clubs.values():
        club["players"].sort(key=lambda p: p["rating"], reverse=True)
        club["scores"] = aggregate_club(club["players"])
        club["playerCount"] = len(club["players"])
        club_list.append(club)

    club_list.sort(key=lambda c: c["scores"]["total"], reverse=True)

    return {
        "generatedAt": generated_at,
        "season": config.SEASON,
        "tournament": config.WC_LEAGUE,
        "coverage": {"playersMapped": len(records),
                     "clubs": len(club_list)},
        "clubs": club_list,
    }


def write_standings(standings, path=DEFAULT_OUTPUT):
    """Atomic write, but only if coverage is non-empty. Returns True if written."""
    if standings["coverage"]["playersMapped"] <= 0:
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(standings, f, indent=2)
    os.replace(tmp, path)
    return True


def main(fetch=None, path=DEFAULT_OUTPUT):
    from src.espn_client import fetch_json
    fetch = fetch or fetch_json
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mapping = build_mapping(fetch=fetch)
    records = accumulate_players(mapping, fetch=fetch)
    standings = assemble_standings(records, generated_at=generated_at)
    written = write_standings(standings, path=path)
    print(f"mapped={standings['coverage']['playersMapped']} "
          f"clubs={standings['coverage']['clubs']} written={written}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_build.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: PASS (all tasks 1–8 green).

- [ ] **Step 6: Commit**

```bash
git add src/build.py tests/test_build.py
git commit -m "feat: assemble standings.json with fail-soft atomic write"
```

---

### Task 9: Capture fixtures + live smoke run

**Files:**
- Create: `tests/capture_fixtures.py`, `tests/fixtures/*.json` (generated)
- Create: `tests/test_integration_fixtures.py`

This proves the pipeline against *real* captured ESPN payloads offline, and a live `main()` run confirms end-to-end coverage.

- [ ] **Step 1: Write the fixture capture script**

`tests/capture_fixtures.py`:
```python
"""Download a small set of real ESPN responses for offline tests.

Run once: python3 tests/capture_fixtures.py
"""
import json
import os
from src import config
from src.espn_client import fetch_json

OUT = os.path.join(os.path.dirname(__file__), "fixtures")


def save(name, payload):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(payload, f)
    print("wrote", name)


def main():
    # One Serie A team roster (mapping shape).
    save("ita1_teams.json", fetch_json(f"{config.BASE}/ita.1/teams"))
    save("ita1_team103_roster.json",
         fetch_json(f"{config.BASE}/ita.1/teams/103/roster?season={config.SEASON}"))
    # One completed WC match summary (stats shape).
    save("wc_summary_760416.json",
         fetch_json(f"{config.BASE}/{config.WC_LEAGUE}/summary?event=760416"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the capture script (requires network)**

Run: `python3 tests/capture_fixtures.py`
Expected: writes `tests/fixtures/ita1_teams.json`, `ita1_team103_roster.json`, `wc_summary_760416.json`.

- [ ] **Step 3: Write the fixture-backed integration test**

`tests/test_integration_fixtures.py`:
```python
import json
import os
from src.wc_stats import process_match_summary

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    with open(os.path.join(FIX, name)) as f:
        return json.load(f)


def test_real_roster_has_positions_and_ids():
    roster = load("ita1_team103_roster.json")
    athletes = roster["athletes"]
    assert len(athletes) > 0
    a = athletes[0]
    assert a["id"]
    assert a["position"]["abbreviation"] in {"G", "D", "M", "F"}


def test_real_wc_summary_yields_player_stats():
    summary = load("wc_summary_760416.json")
    # Map every WC roster athlete to a dummy club so we can process the match.
    mapping = {}
    for team in summary["rosters"]:
        for p in team["roster"]:
            pid = p["athlete"]["id"]
            mapping[pid] = {"club": "X", "league": "eng.1",
                            "leagueName": "Premier League",
                            "position": p.get("position", {}).get("abbreviation") or "M"}
    acc = {}
    process_match_summary(summary, mapping, acc)
    assert len(acc) > 0
    # at least one featured player accumulated real minutes
    assert any(r["minutes"] > 0 for r in acc.values())
    # stats keys include the known fields
    some = next(iter(acc.values()))
    assert "stats" in some and isinstance(some["stats"], dict)
```

- [ ] **Step 4: Run the integration test**

Run: `python3 -m pytest tests/test_integration_fixtures.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Live end-to-end smoke run (requires network)**

Run: `python3 -m src.build`
Expected: prints `mapped=<N> clubs=<M> written=True` with N in the hundreds (depends on how many WC matches have been played), and creates `web/standings.json`.

Sanity-check the output:
Run: `python3 -c "import json; d=json.load(open('web/standings.json')); print(d['coverage']); print([ (c['club'], c['scores']['total']) for c in d['clubs'][:5] ])"`
Expected: a coverage dict and the top-5 clubs by total.

- [ ] **Step 6: Commit fixtures and the generated standings**

```bash
git add tests/capture_fixtures.py tests/fixtures/ tests/test_integration_fixtures.py web/standings.json
git commit -m "test: capture real ESPN fixtures and add integration smoke test"
```

---

### Task 10: Static frontend

**Files:**
- Create: `web/index.html`, `web/styles.css`, `web/app.js`
- Test: `tests/test_standings_contract.py`

The page loads `standings.json`, renders the combined cross-league table plus per-league tabs, a view toggle (Total / Average / Per-90 / Best XI), and expandable per-club player breakdowns. All client-side.

- [ ] **Step 1: Write the JSON-contract test (guards the frontend's assumptions)**

`tests/test_standings_contract.py`:
```python
from src.build import assemble_standings

REC = {"A1": {"id": "A1", "name": "Saka", "nation": "England", "club": "Arsenal",
              "league": "eng.1", "leagueName": "Premier League", "position": "M",
              "stats": {"totalGoals": 1.0, "appearances": 1.0}, "minutes": 90,
              "matches": 1, "cleanSheets": 0}}


def test_frontend_contract_keys_present():
    s = assemble_standings(REC, generated_at="t")
    assert {"generatedAt", "season", "coverage", "clubs"} <= set(s)
    club = s["clubs"][0]
    assert {"club", "league", "leagueName", "scores", "playerCount", "players"} <= set(club)
    assert {"total", "average", "per90", "bestXI"} == set(club["scores"])
    player = club["players"][0]
    assert {"name", "position", "nation", "minutes", "rating", "breakdown"} <= set(player)
    assert {"label", "points"} <= set(player["breakdown"][0])
```

- [ ] **Step 2: Run it**

Run: `python3 -m pytest tests/test_standings_contract.py -q`
Expected: PASS (1 passed). (This locks the contract `app.js` relies on.)

- [ ] **Step 3: Create `web/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>World Cup Club Bragging Board</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <header>
    <h1>World Cup Club Bragging Board</h1>
    <p class="sub">Big-five clubs ranked by their players' FIFA World Cup 2026 performance.</p>
  </header>

  <nav class="controls">
    <div id="leagues" class="tabs"></div>
    <div id="views" class="tabs"></div>
  </nav>

  <main>
    <table id="board">
      <thead>
        <tr><th>#</th><th>Club</th><th>League</th><th>Players</th><th id="score-head">Score</th></tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </main>

  <footer>
    <p id="meta"></p>
    <p class="disclaimer">Data: unofficial ESPN endpoints. Players attributed to their 2025–26 club.
      Ratings are derived from match stats; see each club's breakdown.</p>
  </footer>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Create `web/styles.css`**

```css
:root { --bg:#0f1226; --card:#1a1f3c; --ink:#eef; --muted:#9aa; --accent:#34d399; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, sans-serif; background:var(--bg); color:var(--ink); }
header { padding:24px 16px 8px; text-align:center; }
h1 { margin:0; font-size:1.6rem; }
.sub { color:var(--muted); margin:4px 0 0; }
.controls { display:flex; flex-wrap:wrap; gap:16px; justify-content:center; padding:16px; }
.tabs { display:flex; gap:6px; flex-wrap:wrap; }
.tabs button { background:var(--card); color:var(--ink); border:1px solid #333a66;
  padding:6px 12px; border-radius:999px; cursor:pointer; font-size:.85rem; }
.tabs button.active { background:var(--accent); color:#06241a; border-color:var(--accent); font-weight:600; }
main { max-width:820px; margin:0 auto; padding:0 12px 32px; }
table { width:100%; border-collapse:collapse; background:var(--card); border-radius:12px; overflow:hidden; }
th, td { padding:10px 12px; text-align:left; border-bottom:1px solid #2a3056; }
th { font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }
td.score, th#score-head { text-align:right; font-variant-numeric:tabular-nums; }
tr.club-row { cursor:pointer; }
tr.club-row:hover { background:#222a52; }
tr.detail td { background:#11152e; padding:0; }
.players { margin:0; padding:8px 16px; }
.player { display:flex; justify-content:space-between; gap:8px; padding:4px 0;
  border-bottom:1px dashed #2a3056; font-size:.9rem; }
.player .meta { color:var(--muted); font-size:.8rem; }
.breakdown { color:var(--muted); font-size:.78rem; margin-left:8px; }
footer { text-align:center; color:var(--muted); padding:16px; font-size:.8rem; }
.disclaimer { font-size:.72rem; }
```

- [ ] **Step 5: Create `web/app.js`**

```javascript
const VIEWS = [
  { key: "total", label: "Total" },
  { key: "average", label: "Average" },
  { key: "per90", label: "Per-90" },
  { key: "bestXI", label: "Best XI" },
];

let DATA = null;
let currentLeague = "all";
let currentView = "total";

async function load() {
  const res = await fetch("standings.json", { cache: "no-store" });
  DATA = await res.json();
  buildLeagueTabs();
  buildViewTabs();
  render();
  const when = new Date(DATA.generatedAt).toLocaleString();
  document.getElementById("meta").textContent =
    `Updated ${when} · ${DATA.coverage.playersMapped} players · season ${DATA.season}`;
}

function leagues() {
  const map = new Map();
  DATA.clubs.forEach(c => map.set(c.league, c.leagueName));
  return [["all", "All leagues"], ...map.entries()];
}

function buildLeagueTabs() {
  const el = document.getElementById("leagues");
  el.innerHTML = "";
  leagues().forEach(([key, name]) => {
    const b = document.createElement("button");
    b.textContent = name;
    b.className = key === currentLeague ? "active" : "";
    b.onclick = () => { currentLeague = key; buildLeagueTabs(); render(); };
    el.appendChild(b);
  });
}

function buildViewTabs() {
  const el = document.getElementById("views");
  el.innerHTML = "";
  VIEWS.forEach(v => {
    const b = document.createElement("button");
    b.textContent = v.label;
    b.className = v.key === currentView ? "active" : "";
    b.onclick = () => { currentView = v.key; buildViewTabs(); render(); };
    el.appendChild(b);
  });
}

function render() {
  document.getElementById("score-head").textContent =
    VIEWS.find(v => v.key === currentView).label;
  const rows = document.getElementById("rows");
  rows.innerHTML = "";

  const clubs = DATA.clubs
    .filter(c => currentLeague === "all" || c.league === currentLeague)
    .slice()
    .sort((a, b) => b.scores[currentView] - a.scores[currentView]);

  clubs.forEach((c, i) => {
    const tr = document.createElement("tr");
    tr.className = "club-row";
    tr.innerHTML =
      `<td>${i + 1}</td><td>${c.club}</td><td>${c.leagueName}</td>` +
      `<td>${c.playerCount}</td><td class="score">${c.scores[currentView].toFixed(1)}</td>`;
    const detail = document.createElement("tr");
    detail.className = "detail";
    detail.style.display = "none";
    detail.innerHTML = `<td colspan="5">${playersHtml(c)}</td>`;
    tr.onclick = () => {
      detail.style.display = detail.style.display === "none" ? "" : "none";
    };
    rows.appendChild(tr);
    rows.appendChild(detail);
  });
}

function playersHtml(club) {
  const items = club.players.map(p => {
    const parts = p.breakdown
      .map(b => `${b.label} ${b.points > 0 ? "+" : ""}${b.points}`)
      .join(", ");
    return `<div class="player">
      <span>${p.name} <span class="meta">(${p.position}, ${p.nation}, ${p.minutes}')</span></span>
      <span>${p.rating.toFixed(1)} <span class="breakdown">${parts}</span></span>
    </div>`;
  }).join("");
  return `<div class="players">${items}</div>`;
}

load();
```

- [ ] **Step 6: Manual verification in a browser**

Run (serves the `web/` dir; uses the `standings.json` produced in Task 9):
```bash
python3 -m http.server 8000 --directory web
```
Open `http://localhost:8000/`. Verify:
- The combined table lists clubs with ranks and a score.
- Switching league tabs filters; switching view tabs re-sorts and relabels the score column.
- Clicking a club row expands the player list with rating breakdowns.
Stop the server with Ctrl-C.

- [ ] **Step 7: Commit**

```bash
git add web/index.html web/styles.css web/app.js tests/test_standings_contract.py
git commit -m "feat: static frontend with league tabs, view toggle and breakdowns"
```

---

### Task 11: GitHub Action (cron + Pages) and README

**Files:**
- Create: `.github/workflows/build.yml`, `README.md`
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
*.tmp
```

- [ ] **Step 2: Create the workflow**

`.github/workflows/build.yml`:
```yaml
name: Build standings

on:
  schedule:
    - cron: "*/15 * * * *"   # every 15 min (GitHub may delay during busy periods)
  workflow_dispatch:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: build-standings
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run pipeline (keeps last good standings.json on failure)
        run: |
          python3 -m src.build || echo "pipeline reported no write; keeping last good file"
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: web
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

Note: the committed `web/standings.json` (from Task 9) is checked out each run, so even if a run can't fetch fresh data the last good file is what gets deployed.

- [ ] **Step 3: Create `README.md`**

```markdown
# World Cup Club Bragging Board

Ranks Europe's big-five-league clubs by how their players perform at the FIFA
World Cup 2026. Static site, rebuilt every ~15 minutes via GitHub Actions.

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
python3 -m pytest -q          # run tests
python3 -m src.build          # regenerate web/standings.json (needs network)
python3 -m http.server 8000 --directory web   # preview
```

## Tuning the scoring
Edit `src/weights.py` — it is the single source of truth for the rating model.

## Caveat
Uses unofficial ESPN endpoints; shapes can change. The pipeline fails soft and
keeps the last good `standings.json`.
```

- [ ] **Step 4: Verify tests still pass**

Run: `python3 -m pytest -q`
Expected: PASS (entire suite).

- [ ] **Step 5: Commit**

```bash
git add .gitignore .github/workflows/build.yml README.md
git commit -m "chore: GitHub Actions cron build + Pages deploy and README"
```

- [ ] **Step 6: (Manual, post-merge) Enable Pages**

In GitHub repo Settings → Pages → Source: "GitHub Actions". Trigger the workflow
via "Run workflow" (workflow_dispatch) and confirm the deployed URL renders.

---

## Self-review (completed)

**Spec coverage:**
- Data source / endpoints → Verified-facts block + Tasks 5–7. ✓
- Auto mapping via athlete ID + `season=2025` → Task 6 (`roster_url` pins season). ✓
- Position-aware rating + transparent breakdown → Task 2 + weights (Task 1). ✓
- Four aggregation views → Task 3. ✓
- Combined + per-league layout, view toggle, breakdowns → Task 10. ✓
- Static page rebuilt on schedule, free hosting → Task 11. ✓
- Fail-soft / keep last good file → Task 8 (`write_standings`) + Task 11 note. ✓
- Completed/in-progress matches only → `collect_event_ids` filters state `pre`. ✓
- Minutes from subs, clean sheets from team score → Task 4 + Task 7. ✓
- Testing strategy (pure unit + fixtures + smoke) → Tasks 2–4 (pure), 9 (fixtures/smoke). ✓
- `accuratePasses`/`defensiveInterventions` excluded (not per-player) → noted; weights omit them. ✓

**Placeholder scan:** none — every code step is complete and runnable.

**Type consistency:** record schema (`id,name,nation,club,league,leagueName,position,stats,minutes,matches,cleanSheets`) is produced in Task 7 and consumed unchanged in Tasks 2 (`position`,`stats`,`cleanSheets`), 3 (`rating`,`minutes`), 8 (all). `scores` keys `{total,average,per90,bestXI}` consistent across Tasks 3, 8, 10. `breakdown` items `{label,points}` consistent across Tasks 2, 10, contract test.
