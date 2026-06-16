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
