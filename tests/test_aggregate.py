from src.aggregate import aggregate_club


def test_four_views():
    players = [
        {"rating": 10.0, "minutes": 90},
        {"rating": 6.0, "minutes": 45},
        {"rating": 2.0, "minutes": 90},
    ]
    s = aggregate_club(players)
    assert s["total"] == 18.0
    assert s["average"] == 6.0                      # 18 / 3
    # per90 = 18 / (225/90) = 18 / 2.5 = 7.2
    assert s["per90"] == 7.2
    assert s["bestXI"] == 18.0                       # fewer than 11 -> all


def test_best_xi_caps_at_eleven():
    players = [{"rating": float(i), "minutes": 90} for i in range(1, 14)]  # 1..13
    s = aggregate_club(players)
    # top 11 of 1..13 = 3..13 sum = (3+13)*11/2 = 88
    assert s["bestXI"] == 88.0
    assert s["total"] == 91.0                        # 1..13 sum


def test_empty_club_is_zeroed():
    s = aggregate_club([])
    assert s == {"total": 0.0, "average": 0.0, "per90": 0.0, "bestXI": 0.0}


def test_per90_zero_when_no_minutes():
    s = aggregate_club([{"rating": 5.0, "minutes": 0}])
    assert s["per90"] == 0.0
