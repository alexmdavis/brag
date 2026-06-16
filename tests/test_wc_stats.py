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
