from src import config
from src.mapping import build_mapping, teams_url, roster_url, standings_url


def test_url_builders():
    assert teams_url("ita.1") == f"{config.BASE}/ita.1/teams"
    assert roster_url("ita.1", "103") == f"{config.BASE}/ita.1/teams/103/roster?season={config.SEASON}"
    assert standings_url("ita.1", 2025) == f"{config.STANDINGS_BASE}/ita.1/standings?season=2025"


def _standings(entries):
    """entries: list of (id, name, relegated_note_bool)."""
    return {"children": [{"standings": {"entries": [
        {"team": {"id": tid, "displayName": name},
         "note": ({"description": "Relegation"} if rel else None)}
        for tid, name, rel in entries
    ]}}]}


def _roster(name, athletes):
    return {"team": {"displayName": name, "logo": f"crest-{name}"},
            "athletes": [{"id": aid, "displayName": aid, "position": {"abbreviation": "M"}}
                         for aid in athletes]}


PROMOTED = {"eng.1": ["P1"]}
TIER2 = {"eng.1": "eng.2"}


def test_relegated_via_next_season_diff_and_promoted_from_second_tier():
    cur = _standings([("1", "Arsenal", False), ("2", "Wolves", False)])
    nxt = _standings([("1", "Arsenal", False)])              # Wolves gone -> relegated

    def fetch(url, **kwargs):
        if "standings?season=2025" in url: return cur
        if "standings?season=2026" in url: return nxt
        if "/eng.1/teams/1/roster" in url: return _roster("Arsenal", ["A1"])
        if "/eng.1/teams/2/roster" in url: return _roster("Wolves", ["A2"])
        if "/eng.2/teams/P1/roster" in url: return _roster("Coventry City", ["A3"])
        raise AssertionError(f"unexpected url {url}")

    m = build_mapping(fetch=fetch, leagues={"eng.1": "Premier League"},
                      promoted_map=PROMOTED, second_tier=TIER2)
    assert m["A1"]["promoted"] is False and m["A1"]["relegated"] is False
    assert m["A2"]["relegated"] is True and m["A2"]["promoted"] is False
    assert m["A3"]["promoted"] is True and m["A3"]["relegated"] is False
    assert m["A3"]["club"] == "Coventry City"


def test_relegated_falls_back_to_note_when_no_next_season():
    cur = _standings([("1", "Arsenal", False), ("2", "Wolves", True)])  # note marks relegation

    def fetch(url, **kwargs):
        if "standings?season=2025" in url: return cur
        if "standings?season=2026" in url: raise OSError("no upcoming season yet")
        if "/eng.1/teams/1/roster" in url: return _roster("Arsenal", ["A1"])
        if "/eng.1/teams/2/roster" in url: return _roster("Wolves", ["A2"])
        if "/eng.2/teams/P1/roster" in url: return _roster("Coventry City", ["A3"])
        raise AssertionError(f"unexpected url {url}")

    m = build_mapping(fetch=fetch, leagues={"eng.1": "Premier League"},
                      promoted_map=PROMOTED, second_tier=TIER2)
    assert m["A2"]["relegated"] is True
    assert m["A3"]["promoted"] is True


def test_no_second_tier_means_no_relegation():
    # MLS-like league: no promotion/relegation. Even when next-season membership
    # differs, clubs must never be flagged relegated (the diff must not run).
    cur = _standings([("1", "Columbus Crew", False), ("2", "LA Galaxy", False)])
    nxt = _standings([("1", "Columbus Crew", False)])   # Galaxy "missing" — but MLS has no relegation

    def fetch(url, **kwargs):
        if "standings?season=2025" in url: return cur
        if "standings?season=2026" in url: return nxt
        if "/usa.1/teams/1/roster" in url: return _roster("Columbus Crew", ["A1"])
        if "/usa.1/teams/2/roster" in url: return _roster("LA Galaxy", ["A2"])
        raise AssertionError(f"unexpected url {url}")

    m = build_mapping(fetch=fetch, leagues={"usa.1": "MLS"},
                      promoted_map={}, second_tier={})
    assert m["A1"]["relegated"] is False and m["A1"]["promoted"] is False
    assert m["A2"]["relegated"] is False and m["A2"]["promoted"] is False


def test_failed_club_roster_is_skipped():
    cur = _standings([("1", "Arsenal", False), ("2", "Wolves", False)])
    nxt = _standings([("1", "Arsenal", False), ("2", "Wolves", False)])

    def fetch(url, **kwargs):
        if "standings?season=2025" in url: return cur
        if "standings?season=2026" in url: return nxt
        if "/eng.1/teams/2/roster" in url: raise OSError("boom")
        if "/eng.1/teams/1/roster" in url: return _roster("Arsenal", ["A1"])
        if "/eng.2/teams/P1/roster" in url: return _roster("Coventry City", ["A3"])
        raise AssertionError(f"unexpected url {url}")

    m = build_mapping(fetch=fetch, leagues={"eng.1": "Premier League"},
                      promoted_map=PROMOTED, second_tier=TIER2)
    assert set(m) == {"A1", "A3"}        # failed Wolves roster skipped, no crash
