from src import config
from src.mapping import build_mapping, teams_url, roster_url


def test_url_builders():
    assert teams_url("ita.1") == f"{config.BASE}/ita.1/teams"
    assert roster_url("ita.1", "103") == f"{config.BASE}/ita.1/teams/103/roster?season={config.SEASON}"


def fake_fetch_factory():
    teams_payload = {"sports": [{"leagues": [{"teams": [
        {"team": {"id": "103", "displayName": "AC Milan"}},
    ]}]}]}
    roster_payload = {
        "team": {"displayName": "AC Milan",
                 "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png"},
        "athletes": [
            {"id": "225607", "displayName": "Christian Pulisic", "position": {"abbreviation": "M"}},
            {"id": "236210", "displayName": "Fikayo Tomori", "position": {"abbreviation": "D"}},
        ]}

    def fetch(url, **kwargs):
        if url.endswith("/teams"):
            return teams_payload
        if "/roster" in url:
            return roster_payload
        raise AssertionError(f"unexpected url {url}")
    return fetch


def test_build_mapping_indexes_by_athlete_id():
    m = build_mapping(fetch=fake_fetch_factory(), leagues={"ita.1": "Serie A"})
    assert m["225607"] == {
        "club": "AC Milan", "league": "ita.1",
        "leagueName": "Serie A", "position": "M",
        "clubLogo": "https://a.espncdn.com/i/teamlogos/soccer/500/103.png",
    }
    assert m["236210"]["position"] == "D"
    assert m["236210"]["clubLogo"].endswith("/103.png")


def test_build_mapping_skips_failed_team():
    def fetch(url, **kwargs):
        if url.endswith("/teams"):
            return {"sports": [{"leagues": [{"teams": [
                {"team": {"id": "1", "displayName": "Good"}},
                {"team": {"id": "2", "displayName": "Bad"}},
            ]}]}]}
        if "/teams/2/roster" in url:
            raise OSError("boom")
        return {"team": {"displayName": "Good", "logo": "x"}, "athletes": [
            {"id": "11", "displayName": "A", "position": {"abbreviation": "F"}}]}
    m = build_mapping(fetch=fetch, leagues={"eng.1": "Premier League"})
    assert "11" in m
    assert len(m) == 1
    assert m["11"]["clubLogo"] == "x"
