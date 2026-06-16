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
