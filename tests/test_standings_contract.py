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
