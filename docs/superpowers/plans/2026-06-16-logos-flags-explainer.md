# Logos/Flags + Scoring Explainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add league logos, club crests, national flags, and player headshots to the board, plus an in-page "How scoring works" panel generated from the weights.

**Architecture:** Extends the existing compute-once-into-`standings.json` pipeline. Image URLs are captured during the existing fetches (club crest from domestic roster, national flag from WC summary) or derived (headshot from athlete id, league logo from a static map). A new pure module `methodology.py` turns `weights.py` into a `methodology` block embedded in `standings.json`. The static page renders all of it client-side with `onerror` fallbacks.

**Tech Stack:** Python 3 (stdlib), pytest, vanilla HTML/CSS/JS.

---

## Verified facts (proven live 2026-06-16)

- Club crest: `roster.team.logo` → `https://a.espncdn.com/i/teamlogos/soccer/500/{teamId}.png` (full coverage; already in the mapping fetch).
- National flag: WC summary `rosters[].team.logos[0].href` → `https://a.espncdn.com/i/teamlogos/countries/500/{abbr}.png` (full coverage; already in the summary fetch).
- League logo (HTTP 200 verified): `eng.1`→23, `esp.1`→15, `ita.1`→12, `fra.1`→9, `ger.1`→10 at `https://a.espncdn.com/i/leaguelogos/soccer/500/{n}.png`.
- Player headshot: `https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png` — **partial coverage (~50–60%)**; needs fallback headshot→flag→initials.

## Current record schema (produced by `wc_stats.py`, consumed by `build.py`)

```
{id, name, nation, club, league, leagueName, position, stats, minutes, matches, cleanSheets}
```
This plan adds `clubLogo`, `nationFlag`, `headshot` to records, and `clubLogo`/`leagueLogo` to club objects, `nationFlag`/`headshot` to player objects, and a top-level `methodology` to `standings.json`.

---

### Task 1: Config constants for logos

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_config.py`:
```python
def test_league_logos_cover_all_leagues():
    assert set(config.LEAGUE_LOGOS) == set(config.LEAGUES)
    assert config.LEAGUE_LOGOS["eng.1"].endswith("/23.png")
    assert all(u.startswith("https://a.espncdn.com/") for u in config.LEAGUE_LOGOS.values())


def test_headshot_url_has_id_placeholder():
    assert "{id}" in config.HEADSHOT_URL
    assert config.HEADSHOT_URL.format(id="225607").endswith("/225607.png")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: FAIL (`AttributeError: module 'src.config' has no attribute 'LEAGUE_LOGOS'`).

- [ ] **Step 3: Add constants to `src/config.py`**

Append to the end of `src/config.py`:
```python
# ESPN CDN league-logo URLs (verified HTTP 200, keyed by league code).
LEAGUE_LOGOS = {
    "eng.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png",
    "esp.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png",
    "ita.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png",
    "fra.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png",
    "ger.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png",
}

# Player headshot URL template (partial coverage; frontend falls back to flag/initials).
HEADSHOT_URL = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add league-logo and headshot URL config"
```

---

### Task 2: Methodology module (pure)

**Files:**
- Create: `src/methodology.py`
- Test: `tests/test_methodology.py`

- [ ] **Step 1: Write the failing test**

`tests/test_methodology.py`:
```python
from src import weights
from src.methodology import build_methodology


def test_methodology_structure():
    m = build_methodology(weights)
    assert m["positionGroups"] == {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"}
    assert set(m["weights"]) == {"GK", "DEF", "MID", "FWD"}
    # weights mirror the source of truth
    assert m["weights"]["FWD"]["totalGoals"] == weights.WEIGHTS["FWD"]["totalGoals"]
    assert m["cleanSheetBonus"]["GK"] == weights.CLEAN_SHEET_BONUS["GK"]
    assert m["appearancePoints"] == weights.APPEARANCE_POINTS
    assert m["fieldLabels"]["totalGoals"] == "Goals"


def test_methodology_views_and_notes():
    m = build_methodology(weights)
    keys = [v["key"] for v in m["views"]]
    assert keys == ["total", "average", "per90", "bestXI"]
    assert all(v["formula"] for v in m["views"])
    assert isinstance(m["notes"], list) and len(m["notes"]) >= 3


def test_methodology_is_a_copy_not_references():
    m = build_methodology(weights)
    m["weights"]["FWD"]["totalGoals"] = -999
    assert weights.WEIGHTS["FWD"]["totalGoals"] != -999   # source untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_methodology.py -q`
Expected: FAIL (`ModuleNotFoundError: src.methodology`).

- [ ] **Step 3: Implement `src/methodology.py`**

```python
def build_methodology(weights):
    """Turn the weights module into a JSON-serializable methodology dict.

    Pure: returns copies so the caller can't mutate the source of truth.
    """
    views = [
        {"key": "total", "label": "Total",
         "formula": "Sum of every player's rating for the club."},
        {"key": "average", "label": "Average",
         "formula": "Mean rating across the club's World Cup players."},
        {"key": "per90", "label": "Per-90",
         "formula": "Total rating divided by (total minutes / 90)."},
        {"key": "bestXI", "label": "Best XI",
         "formula": "Sum of the club's top 11 player ratings."},
    ]
    notes = [
        "Players are attributed to their 2025–26 club.",
        "Stats come from completed or in-progress World Cup matches via ESPN.",
        "A clean sheet = a match the player featured in where his team conceded 0 goals.",
        "A small appearance bonus rewards simply featuring.",
    ]
    return {
        "positionGroups": dict(weights.POSITION_GROUPS),
        "weights": {group: dict(fields) for group, fields in weights.WEIGHTS.items()},
        "cleanSheetBonus": dict(weights.CLEAN_SHEET_BONUS),
        "appearancePoints": weights.APPEARANCE_POINTS,
        "fieldLabels": dict(weights.FIELD_LABELS),
        "views": views,
        "notes": notes,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_methodology.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/methodology.py tests/test_methodology.py
git commit -m "feat: methodology dict generated from weights"
```

---

### Task 3: Mapping captures club crest

**Files:**
- Modify: `src/mapping.py`
- Test: `tests/test_mapping.py`

- [ ] **Step 1: Update the test (full new content)**

Replace `tests/test_mapping.py` with:
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
    roster_payload = {
        "team": {"displayName": "AC Milan",
                 "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png"},
        "athletes": [
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
    m = build_mapping(fetch=fake_fetch_factory(), leagues={"ita.1": "Serie A"})
    assert m["225607"] == {
        "club": "AC Milan", "league": "ita.1",
        "leagueName": "Serie A", "position": "M",
        "clubLogo": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png",
    }
    assert m["236210"]["position"] == "D"
    assert m["236210"]["clubLogo"].endswith("/103.png")


def test_build_mapping_skips_failed_team():
    def fetch(url, **kwargs):
        if url.endswith("/teams"):
            return {"sports": [{"leagues": [{"teams": [
                {"team": {"id": "1", "displayName": "Good"}},
                {"team": {"id": "2", "displayName": "Bad"}},
            ]}]}]}
        if "/teams/2/roster" in url:
            raise OSError("boom")
        return {"team": {"displayName": "Good", "logo": "x"}, "athletes": [
            {"id": "11", "displayName": "A", "position": {"abbreviation": "F"}}]}
    m = build_mapping(fetch=fetch, leagues={"eng.1": "Premier League"})
    assert "11" in m
    assert len(m) == 1
    assert m["11"]["clubLogo"] == "x"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_mapping.py -q`
Expected: FAIL (`KeyError`/assert on missing `clubLogo`).

- [ ] **Step 3: Add `clubLogo` capture in `src/mapping.py`**

In `build_mapping`, inside the `for ath in roster.get("athletes", [])` loop, change the `mapping[aid] = {...}` assignment to include the club logo (captured once per roster just before the athlete loop). Replace the block:
```python
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
```
with:
```python
            club = roster.get("team", {}).get("displayName") or entry["team"].get("displayName")
            club_logo = roster.get("team", {}).get("logo")
            for ath in roster.get("athletes", []):
                aid = ath.get("id")
                if not aid:
                    continue
                mapping[aid] = {
                    "club": club,
                    "league": league,
                    "leagueName": league_name,
                    "position": (ath.get("position", {}) or {}).get("abbreviation"),
                    "clubLogo": club_logo,
                }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_mapping.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/mapping.py tests/test_mapping.py
git commit -m "feat: capture club crest URL in mapping"
```

---

### Task 4: WC stats captures flag, headshot, club crest

**Files:**
- Modify: `src/wc_stats.py`
- Test: `tests/test_wc_stats.py`

- [ ] **Step 1: Update the test (full new content)**

Replace `tests/test_wc_stats.py` with:
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
        {"team": {"id": "T1", "displayName": "England",
                  "logos": [{"href": "flag-eng"}, {"href": "flag-eng-dark"}]},
         "roster": [
            {"athlete": {"id": "A1", "displayName": "Saka"}, "starter": True,
             "subbedIn": False, "subbedOut": False,
             "stats": [{"name": "totalGoals", "value": 1.0},
                       {"name": "appearances", "value": 1.0},
                       {"name": "goalsConceded", "value": 0.0}]},
            {"athlete": {"id": "A2", "displayName": "Bench"}, "starter": False,
             "subbedIn": True, "subbedOut": False,
             "stats": [{"name": "appearances", "value": 1.0}]},
        ]},
        {"team": {"id": "T2", "displayName": "France", "logos": [{"href": "flag-fra"}]},
         "roster": [
            {"athlete": {"id": "U1", "displayName": "Unmapped"}, "starter": True,
             "subbedIn": False, "subbedOut": False, "stats": []},
        ]},
    ],
}

MAPPING = {
    "A1": {"club": "Arsenal", "league": "eng.1", "leagueName": "Premier League",
           "position": "M", "clubLogo": "crest-ars"},
    "A2": {"club": "Chelsea", "league": "eng.1", "leagueName": "Premier League",
           "position": "F", "clubLogo": "crest-che"},
}


def test_team_goals_conceded():
    assert team_goals_conceded(SUMMARY) == {"T1": 0, "T2": 2}


def test_process_captures_images():
    acc = {}
    process_match_summary(SUMMARY, MAPPING, acc)
    assert set(acc) == {"A1", "A2"}

    a1 = acc["A1"]
    assert a1["nationFlag"] == "flag-eng"          # first/default logo variant
    assert a1["clubLogo"] == "crest-ars"           # carried from mapping
    assert a1["headshot"].endswith("/A1.png")      # derived from athlete id
    assert a1["minutes"] == 90
    assert a1["cleanSheets"] == 1

    assert acc["A2"]["nationFlag"] == "flag-eng"
    assert acc["A2"]["headshot"].endswith("/A2.png")


def test_process_is_additive_across_matches():
    acc = {}
    process_match_summary(SUMMARY, MAPPING, acc)
    process_match_summary(SUMMARY, MAPPING, acc)
    assert acc["A1"]["stats"]["totalGoals"] == 2.0
    assert acc["A1"]["matches"] == 2
    assert acc["A1"]["nationFlag"] == "flag-eng"   # stable, not duplicated
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wc_stats.py -q`
Expected: FAIL (missing `nationFlag`/`headshot`/`clubLogo`).

- [ ] **Step 3: Update `src/wc_stats.py`**

Add the config import at the top (alongside the existing `from src import config`):
```python
from src.config import HEADSHOT_URL
```

Replace `_new_record` with (adds `clubLogo`, `nationFlag`, `headshot`):
```python
def _new_record(pid, player, info, nation, nation_flag):
    return {
        "id": pid,
        "name": player.get("athlete", {}).get("displayName"),
        "nation": nation,
        "nationFlag": nation_flag,
        "headshot": HEADSHOT_URL.format(id=pid),
        "club": info["club"],
        "league": info["league"],
        "leagueName": info["leagueName"],
        "position": info["position"],
        "clubLogo": info.get("clubLogo"),
        "stats": {},
        "minutes": 0,
        "matches": 0,
        "cleanSheets": 0,
    }
```

In `process_match_summary`, replace the team loop header and the `_new_record` call. Change:
```python
    for team in summary.get("rosters", []) or []:
        nation = team.get("team", {}).get("displayName")
        team_id = team.get("team", {}).get("id")
```
to:
```python
    for team in summary.get("rosters", []) or []:
        team_obj = team.get("team", {})
        nation = team_obj.get("displayName")
        team_id = team_obj.get("id")
        nation_flag = (team_obj.get("logos") or [{}])[0].get("href")
```
and change:
```python
            rec = acc.get(pid) or _new_record(pid, player, info, nation)
```
to:
```python
            rec = acc.get(pid) or _new_record(pid, player, info, nation, nation_flag)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_wc_stats.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wc_stats.py tests/test_wc_stats.py
git commit -m "feat: capture national flag, headshot and crest in WC records"
```

---

### Task 5: Build threads images + embeds methodology

**Files:**
- Modify: `src/build.py`
- Test: `tests/test_build.py`, `tests/test_standings_contract.py`

- [ ] **Step 1: Update the build test (full new content)**

Replace `tests/test_build.py` with:
```python
import json
from src.build import assemble_standings, write_standings


RECORDS = {
    "A1": {"id": "A1", "name": "Saka", "nation": "England", "nationFlag": "flag-eng",
           "headshot": "shot-A1", "club": "Arsenal", "league": "eng.1",
           "leagueName": "Premier League", "position": "M", "clubLogo": "crest-ars",
           "stats": {"totalGoals": 2.0, "goalAssists": 1.0, "appearances": 2.0},
           "minutes": 180, "matches": 2, "cleanSheets": 0},
    "A2": {"id": "A2", "name": "Saliba", "nation": "France", "nationFlag": "flag-fra",
           "headshot": "shot-A2", "club": "Arsenal", "league": "eng.1",
           "leagueName": "Premier League", "position": "D", "clubLogo": "crest-ars",
           "stats": {"appearances": 1.0}, "minutes": 90, "matches": 1, "cleanSheets": 1},
}


def test_assemble_threads_images_and_methodology():
    s = assemble_standings(RECORDS, generated_at="2026-06-16T18:00:00Z")
    assert s["coverage"]["playersMapped"] == 2
    club = s["clubs"][0]
    assert club["clubLogo"] == "crest-ars"
    assert club["leagueLogo"].endswith("/23.png")          # eng.1 league logo
    player = club["players"][0]
    assert player["nationFlag"] in {"flag-eng", "flag-fra"}
    assert player["headshot"] in {"shot-A1", "shot-A2"}
    # methodology embedded from weights
    assert "methodology" in s
    assert set(s["methodology"]["weights"]) == {"GK", "DEF", "MID", "FWD"}
    assert [v["key"] for v in s["methodology"]["views"]] == \
        ["total", "average", "per90", "bestXI"]


def test_clubs_sorted_by_total_desc():
    recs = dict(RECORDS)
    recs["B1"] = {"id": "B1", "name": "X", "nation": "Spain", "nationFlag": "f",
                  "headshot": "h", "club": "Brighton", "league": "eng.1",
                  "leagueName": "Premier League", "position": "F", "clubLogo": "c",
                  "stats": {"appearances": 1.0}, "minutes": 90, "matches": 1, "cleanSheets": 0}
    s = assemble_standings(recs, generated_at="t")
    totals = [c["scores"]["total"] for c in s["clubs"]]
    assert totals == sorted(totals, reverse=True)


def test_write_is_failsoft_on_empty(tmp_path):
    path = tmp_path / "standings.json"
    good = assemble_standings(RECORDS, generated_at="t1")
    assert write_standings(good, str(path)) is True
    empty = assemble_standings({}, generated_at="t2")
    assert write_standings(empty, str(path)) is False
    on_disk = json.loads(path.read_text())
    assert on_disk["generatedAt"] == "t1"
```

- [ ] **Step 2: Extend the contract test**

Replace `tests/test_standings_contract.py` with:
```python
from src.build import assemble_standings

REC = {"A1": {"id": "A1", "name": "Saka", "nation": "England", "nationFlag": "flag-eng",
              "headshot": "shot-A1", "club": "Arsenal", "league": "eng.1",
              "leagueName": "Premier League", "position": "M", "clubLogo": "crest-ars",
              "stats": {"totalGoals": 1.0, "appearances": 1.0}, "minutes": 90,
              "matches": 1, "cleanSheets": 0}}


def test_frontend_contract_keys_present():
    s = assemble_standings(REC, generated_at="t")
    assert {"generatedAt", "season", "coverage", "clubs", "methodology"} <= set(s)
    club = s["clubs"][0]
    assert {"club", "league", "leagueName", "scores", "playerCount",
            "players", "clubLogo", "leagueLogo"} <= set(club)
    assert {"total", "average", "per90", "bestXI"} == set(club["scores"])
    player = club["players"][0]
    assert {"name", "position", "nation", "minutes", "rating", "breakdown",
            "nationFlag", "headshot"} <= set(player)
    assert {"label", "points"} <= set(player["breakdown"][0])
    m = s["methodology"]
    assert {"weights", "views", "positionGroups", "fieldLabels", "notes"} <= set(m)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_build.py tests/test_standings_contract.py -q`
Expected: FAIL (missing `clubLogo`/`leagueLogo`/`methodology`).

- [ ] **Step 4: Update `src/build.py`**

Add imports near the existing imports:
```python
from src import config, weights
from src.methodology import build_methodology
```
(Note: replace the existing `from src import config` line with `from src import config, weights`.)

In `assemble_standings`, change the player dict and the club `setdefault` to include images. Replace:
```python
        player = {
            "id": rec["id"], "name": rec["name"], "position": rec["position"],
            "nation": rec["nation"], "minutes": rec["minutes"],
            "rating": rated["rating"], "breakdown": rated["breakdown"],
        }
        club = clubs.setdefault(rec["club"], {
            "club": rec["club"], "league": rec["league"],
            "leagueName": rec["leagueName"], "players": [],
        })
```
with:
```python
        player = {
            "id": rec["id"], "name": rec["name"], "position": rec["position"],
            "nation": rec["nation"], "nationFlag": rec.get("nationFlag"),
            "headshot": rec.get("headshot"), "minutes": rec["minutes"],
            "rating": rated["rating"], "breakdown": rated["breakdown"],
        }
        club = clubs.setdefault(rec["club"], {
            "club": rec["club"], "league": rec["league"],
            "leagueName": rec["leagueName"],
            "clubLogo": rec.get("clubLogo"),
            "leagueLogo": config.LEAGUE_LOGOS.get(rec["league"]),
            "players": [],
        })
```

In the `return {...}` of `assemble_standings`, add the methodology key. Change:
```python
    return {
        "generatedAt": generated_at,
        "season": config.SEASON,
        "tournament": config.WC_LEAGUE,
        "coverage": {"playersMapped": len(records),
                     "clubs": len(club_list)},
        "clubs": club_list,
    }
```
to:
```python
    return {
        "generatedAt": generated_at,
        "season": config.SEASON,
        "tournament": config.WC_LEAGUE,
        "coverage": {"playersMapped": len(records),
                     "clubs": len(club_list)},
        "methodology": build_methodology(weights),
        "clubs": club_list,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_build.py tests/test_standings_contract.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest -q`
Expected: PASS (all green).

- [ ] **Step 7: Commit**

```bash
git add src/build.py tests/test_build.py tests/test_standings_contract.py
git commit -m "feat: thread logos/flags into standings and embed methodology"
```

---

### Task 6: Frontend — render images + explainer panel

**Files:**
- Modify: `web/index.html`, `web/app.js`, `web/styles.css`

- [ ] **Step 1: Replace `web/index.html`**

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
    <button id="explainer-toggle" class="link-btn">How scoring works</button>
  </nav>

  <section id="explainer" class="hidden"></section>

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
      Logos/flags via ESPN. Ratings are derived from match stats; see “How scoring works”.</p>
  </footer>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Replace `web/app.js`**

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

// Safe element builder. Text is set via textContent, never innerHTML.
function el(tag, opts = {}) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text != null) node.textContent = opts.text;
  if (opts.attrs) {
    for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
  }
  (opts.children || []).forEach(c => c && node.appendChild(c));
  return node;
}

// <img> that removes itself if the URL is missing or fails to load.
function logoImg(src, cls, alt) {
  if (!src) return null;
  const im = document.createElement("img");
  im.className = cls;
  im.alt = alt || "";
  im.title = alt || "";
  im.loading = "lazy";
  im.onerror = () => im.remove();
  im.src = src;
  return im;
}

// Player avatar: headshot -> national flag -> initials.
function avatar(player) {
  const wrap = el("span", { className: "avatar" });
  const initials = (player.name || "?")
    .split(" ").filter(Boolean).map(s => s[0]).slice(0, 2).join("").toUpperCase();
  const showInitials = () =>
    wrap.replaceChildren(el("span", { className: "initials", text: initials || "?" }));
  const showFlag = () => {
    if (!player.nationFlag) return showInitials();
    const f = document.createElement("img");
    f.className = "ava-img"; f.loading = "lazy"; f.alt = player.nation || "";
    f.onerror = showInitials; f.src = player.nationFlag;
    wrap.replaceChildren(f);
  };
  if (player.headshot) {
    const h = document.createElement("img");
    h.className = "ava-img"; h.loading = "lazy"; h.alt = player.name || "";
    h.onerror = showFlag; h.src = player.headshot;
    wrap.appendChild(h);
  } else {
    showFlag();
  }
  return wrap;
}

function leagueLogoMap() {
  const map = new Map();
  DATA.clubs.forEach(c => { if (c.leagueLogo) map.set(c.league, c.leagueLogo); });
  return map;
}

async function load() {
  const res = await fetch("standings.json", { cache: "no-store" });
  DATA = await res.json();
  buildLeagueTabs();
  buildViewTabs();
  setupExplainer();
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
  const wrap = document.getElementById("leagues");
  const logos = leagueLogoMap();
  wrap.replaceChildren(...leagues().map(([key, name]) => {
    const logo = key === "all" ? null : logoImg(logos.get(key), "tab-logo", name);
    const b = el("button", {
      className: key === currentLeague ? "active" : "",
      children: [logo, el("span", { text: name })],
    });
    b.onclick = () => { currentLeague = key; buildLeagueTabs(); render(); };
    return b;
  }));
}

function buildViewTabs() {
  const wrap = document.getElementById("views");
  wrap.replaceChildren(...VIEWS.map(v => {
    const b = el("button", { text: v.label, className: v.key === currentView ? "active" : "" });
    b.onclick = () => { currentView = v.key; buildViewTabs(); render(); };
    return b;
  }));
}

function render() {
  document.getElementById("score-head").textContent =
    VIEWS.find(v => v.key === currentView).label;
  const rows = document.getElementById("rows");
  const logos = leagueLogoMap();

  const clubs = DATA.clubs
    .filter(c => currentLeague === "all" || c.league === currentLeague)
    .slice()
    .sort((a, b) => b.scores[currentView] - a.scores[currentView]);

  const nodes = [];
  clubs.forEach((c, i) => {
    const clubCell = el("td", { className: "club-cell", children: [
      logoImg(c.clubLogo, "crest", c.club),
      el("span", { text: c.club }),
    ]});
    const leagueCell = el("td", { className: "league-cell", children: [
      logoImg(logos.get(c.league), "league-logo", c.leagueName),
      el("span", { text: c.leagueName }),
    ]});
    const tr = el("tr", { className: "club-row", children: [
      el("td", { text: String(i + 1) }),
      clubCell,
      leagueCell,
      el("td", { text: String(c.playerCount) }),
      el("td", { className: "score", text: c.scores[currentView].toFixed(1) }),
    ]});
    const detail = el("tr", { className: "detail", children: [
      el("td", { attrs: { colspan: "5" }, children: [playersNode(c)] }),
    ]});
    detail.style.display = "none";
    tr.onclick = () => {
      detail.style.display = detail.style.display === "none" ? "" : "none";
    };
    nodes.push(tr, detail);
  });
  rows.replaceChildren(...nodes);
}

function playersNode(club) {
  const wrap = el("div", { className: "players" });
  club.players.forEach(p => {
    const parts = p.breakdown
      .map(b => `${b.label} ${b.points > 0 ? "+" : ""}${b.points}`)
      .join(", ");
    const metaChildren = [
      logoImg(p.nationFlag, "flag", p.nation),
      el("span", { text: `${p.position}, ${p.nation}, ${p.minutes}'` }),
    ];
    const left = el("span", { className: "player-left", children: [
      avatar(p),
      el("span", { children: [
        el("span", { className: "pname", text: p.name }),
        el("span", { className: "meta", children: metaChildren }),
      ]}),
    ]});
    const right = el("span", { children: [
      document.createTextNode(p.rating.toFixed(1) + " "),
      el("span", { className: "breakdown", text: parts }),
    ]});
    wrap.appendChild(el("div", { className: "player", children: [left, right] }));
  });
  return wrap;
}

function setupExplainer() {
  const btn = document.getElementById("explainer-toggle");
  const panel = document.getElementById("explainer");
  let built = false;
  btn.onclick = () => {
    if (!built) { panel.replaceChildren(explainerNode(DATA.methodology)); built = true; }
    panel.classList.toggle("hidden");
  };
}

function explainerNode(m) {
  const wrap = el("div", { className: "explainer-inner" });
  wrap.appendChild(el("h2", { text: "How scoring works" }));
  wrap.appendChild(el("p", {
    text: "Each player gets a position-aware rating from their World Cup match stats. "
        + "Clubs are then ranked four ways:",
  }));

  const views = el("ul", { className: "views" });
  m.views.forEach(v =>
    views.appendChild(el("li", { children: [
      el("strong", { text: v.label + ": " }),
      el("span", { text: v.formula }),
    ]})));
  wrap.appendChild(views);

  // Weights table: rows = stat labels, columns = position groups.
  const groups = ["GK", "DEF", "MID", "FWD"];
  const fields = Object.keys(m.fieldLabels);
  const table = el("table", { className: "weights" });
  const head = el("tr", { children: [
    el("th", { text: "Stat" }),
    ...groups.map(g => el("th", { text: g })),
  ]});
  table.appendChild(el("thead", { children: [head] }));
  const body = el("tbody");
  fields.forEach(f => {
    body.appendChild(el("tr", { children: [
      el("td", { text: m.fieldLabels[f] }),
      ...groups.map(g => {
        const v = m.weights[g][f];
        return el("td", { className: "num", text: v == null ? "" : String(v) });
      }),
    ]}));
  });
  // Clean sheet + appearance rows.
  body.appendChild(el("tr", { children: [
    el("td", { text: "Clean sheet" }),
    ...groups.map(g => el("td", { className: "num", text: String(m.cleanSheetBonus[g]) })),
  ]}));
  body.appendChild(el("tr", { children: [
    el("td", { text: "Appearance" }),
    ...groups.map(() => el("td", { className: "num", text: String(m.appearancePoints) })),
  ]}));
  table.appendChild(body);
  wrap.appendChild(table);

  const notes = el("ul", { className: "notes" });
  m.notes.forEach(n => notes.appendChild(el("li", { text: n })));
  wrap.appendChild(notes);
  return wrap;
}

load();
```

- [ ] **Step 3: Append styles to `web/styles.css`**

Append the following block to the end of `web/styles.css`:
```css
/* logos / flags / avatars */
.link-btn { background:none; border:1px solid #333a66; color:var(--ink); border-radius:999px;
  padding:6px 12px; cursor:pointer; font-size:.85rem; }
.link-btn:hover { border-color:var(--accent); }
.tab-logo { width:16px; height:16px; object-fit:contain; vertical-align:middle; margin-right:6px; }
.tabs button { display:inline-flex; align-items:center; }
.club-cell, .league-cell { }
.club-cell { display:flex; align-items:center; gap:8px; }
.league-cell { color:var(--muted); }
.crest { width:22px; height:22px; object-fit:contain; }
.league-logo { width:20px; height:20px; object-fit:contain; vertical-align:middle; margin-right:6px; }
.player-left { display:flex; align-items:center; gap:10px; }
.avatar, .ava-img { width:30px; height:30px; border-radius:50%; flex:0 0 auto; }
.ava-img { object-fit:cover; background:#222a52; }
.avatar { display:inline-flex; align-items:center; justify-content:center; overflow:hidden; }
.initials { width:30px; height:30px; border-radius:50%; background:#2a3056; color:var(--ink);
  display:inline-flex; align-items:center; justify-content:center; font-size:.7rem; }
.pname { display:block; }
.flag { width:18px; height:12px; object-fit:cover; border-radius:2px; margin-right:5px; vertical-align:middle; }
.meta { display:flex; align-items:center; }

/* explainer panel */
.hidden { display:none; }
#explainer { max-width:820px; margin:0 auto 8px; padding:0 12px; }
.explainer-inner { background:var(--card); border-radius:12px; padding:16px 18px; }
.explainer-inner h2 { margin:0 0 8px; font-size:1.1rem; }
.explainer-inner .views { margin:8px 0; padding-left:18px; }
.explainer-inner .views li { margin:3px 0; }
table.weights { width:100%; border-collapse:collapse; margin:12px 0; }
table.weights th, table.weights td { border-bottom:1px solid #2a3056; padding:5px 8px; text-align:left; font-size:.85rem; }
table.weights td.num, table.weights th:not(:first-child) { text-align:right; font-variant-numeric:tabular-nums; }
.explainer-inner .notes { color:var(--muted); font-size:.8rem; padding-left:18px; }
```

- [ ] **Step 4: Regenerate `standings.json` and verify the page serves**

Run (needs network; produces the new schema):
```bash
python3 -m src.build
```
Expected: `mapped=<N> clubs=<M> written=True`.

Confirm the new keys exist:
```bash
python3 -c "import json; d=json.load(open('web/standings.json')); c=d['clubs'][0]; print('clubLogo:', bool(c['clubLogo']), 'leagueLogo:', bool(c['leagueLogo']), 'methodology:', 'methodology' in d, 'player flag/headshot:', bool(c['players'][0]['nationFlag']), bool(c['players'][0]['headshot']))"
```
Expected: all `True`.

- [ ] **Step 5: Serve and smoke-check assets**

```bash
python3 -m http.server 8731 --directory web >/tmp/brag_srv.log 2>&1 &
SRV=$!
for i in $(seq 1 20); do curl -s -o /dev/null "http://localhost:8731/" && break; done
for f in / styles.css app.js standings.json; do
  echo "$f -> HTTP $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8731/$f)"
done
node --check web/app.js && echo "app.js syntax OK"
kill $SRV 2>/dev/null
```
Expected: all HTTP 200, `app.js syntax OK`.

- [ ] **Step 6: Manual browser verification**

Open `http://localhost:8731/` (re-serve if needed). Verify:
- League tabs show small league logos; the table shows club crests and league logos.
- Expanding a club shows player rows with circular headshots (or flag/initials fallback) and a flag beside each nation.
- "How scoring works" toggles a panel with the four view formulas and the weights table.
Stop the server with Ctrl-C.

- [ ] **Step 7: Commit**

```bash
git add web/index.html web/app.js web/styles.css web/standings.json
git commit -m "feat: render logos, flags, headshots and scoring explainer panel"
```

---

### Task 7: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest -q`
Expected: PASS (all tests across the project green).

- [ ] **Step 2: Confirm fixtures still exercise capture (offline)**

Run: `python3 -m pytest tests/test_integration_fixtures.py -q`
Expected: PASS (the captured fixtures already contain `team.logo`/`team.logos`).

- [ ] **Step 3: Commit any incidental changes**

```bash
git status   # should be clean; if standings.json changed, commit it
```

After this plan, hand off to superpowers:finishing-a-development-branch to merge `feature-logos-explainer` into `main` (which redeploys via the Action).

---

## Self-review (completed)

**Spec coverage:**
- Logo/flag data sources → Tasks 1 (league), 3 (crest), 4 (flag/headshot). ✓
- `standings.json` additions (club logos, player flag/headshot, methodology) → Task 5. ✓
- Methodology generated from weights → Task 2 + embedded in Task 5. ✓
- In-page collapsible explainer → Task 6 (`setupExplainer`/`explainerNode`). ✓
- Frontend logos/flags/headshots with fallback → Task 6 (`logoImg`, `avatar`). ✓
- Headshot→flag→initials fallback → Task 6 `avatar`. ✓
- Error handling (missing URL → hide/fallback) → `logoImg` returns null / `onerror`. ✓
- Testing (pure methodology, capture asserts, contract) → Tasks 2–5. ✓
- Out of scope (no self-hosting, no dark flag logic, no headshot-only) → respected. ✓

**Placeholder scan:** none — all steps contain complete code/commands.

**Type consistency:** record keys added in Task 4 (`clubLogo`, `nationFlag`, `headshot`) are consumed in Task 5 (`rec.get(...)`). `methodology` shape from Task 2 matches the frontend reader in Task 6 (`m.views`, `m.weights[g][f]`, `m.fieldLabels`, `m.cleanSheetBonus`, `m.appearancePoints`, `m.notes`). Club keys `clubLogo`/`leagueLogo` and player keys `nationFlag`/`headshot` consistent across Tasks 5–6 and the contract test.
