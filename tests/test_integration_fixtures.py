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
