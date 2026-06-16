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
