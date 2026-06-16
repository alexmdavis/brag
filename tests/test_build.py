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
