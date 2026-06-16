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
           "position": "M", "clubLogo": "crest-ars", "promoted": True, "relegated": False},
    "A2": {"club": "Chelsea", "league": "eng.1", "leagueName": "Premier League",
           "position": "F", "clubLogo": "crest-che", "promoted": False, "relegated": True},
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

    # promotion/relegation status threads from the mapping into the record
    assert a1["promoted"] is True and a1["relegated"] is False
    assert acc["A2"]["relegated"] is True and acc["A2"]["promoted"] is False


def test_process_is_additive_across_matches():
    acc = {}
    process_match_summary(SUMMARY, MAPPING, acc)
    process_match_summary(SUMMARY, MAPPING, acc)
    assert acc["A1"]["stats"]["totalGoals"] == 2.0
    assert acc["A1"]["matches"] == 2
    assert acc["A1"]["nationFlag"] == "flag-eng"   # stable, not duplicated
