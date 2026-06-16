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
