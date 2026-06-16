from src.minutes import parse_minute, parse_sub_events, compute_minutes


def test_parse_minute():
    assert parse_minute("61'") == 61
    assert parse_minute("45'+2") == 45
    assert parse_minute("90'+4") == 90
    assert parse_minute("") == 0


def test_parse_sub_events():
    key_events = [
        {"type": {"text": "Substitution"}, "clock": {"displayValue": "61'"},
         "participants": [{"athlete": {"id": "1"}}, {"athlete": {"id": "2"}}]},
        {"type": {"text": "Goal"}, "clock": {"displayValue": "70'"},
         "participants": [{"athlete": {"id": "3"}}]},
    ]
    subs = parse_sub_events(key_events)
    assert subs == [{"minute": 61, "ids": {"1", "2"}}]


SUBS = [{"minute": 61, "ids": {"10", "20"}}]


def test_starter_full_match():
    p = {"athlete": {"id": "99"}, "starter": True, "subbedIn": False, "subbedOut": False}
    assert compute_minutes(p, SUBS) == 90


def test_starter_subbed_out():
    p = {"athlete": {"id": "10"}, "starter": True, "subbedIn": False, "subbedOut": True}
    assert compute_minutes(p, SUBS) == 61


def test_sub_came_on():
    p = {"athlete": {"id": "20"}, "starter": False, "subbedIn": True, "subbedOut": False}
    assert compute_minutes(p, SUBS) == 29   # 90 - 61


def test_unused_player_zero():
    p = {"athlete": {"id": "77"}, "starter": False, "subbedIn": False, "subbedOut": False}
    assert compute_minutes(p, SUBS) == 0


def test_subbed_out_without_event_defaults_full():
    p = {"athlete": {"id": "55"}, "starter": True, "subbedIn": False, "subbedOut": True}
    assert compute_minutes(p, []) == 90
