from src import config, weights


def test_five_leagues_with_names():
    assert set(config.LEAGUES) == {"eng.1", "esp.1", "ita.1", "fra.1", "ger.1"}
    assert config.LEAGUES["eng.1"] == "Premier League"


def test_season_is_pinned_int():
    assert config.SEASON == 2025  # 2025-26; rosters are empty without it


def test_base_and_tournament():
    assert config.BASE.endswith("/sports/soccer")
    assert config.WC_LEAGUE == "fifa.world"
    assert config.TOURNAMENT_START == "20260611"
    assert config.TOURNAMENT_END == "20260719"


def test_weights_cover_four_groups():
    assert set(weights.WEIGHTS) == {"GK", "DEF", "MID", "FWD"}
    assert set(weights.POSITION_GROUPS) == {"G", "D", "M", "F"}
    assert set(weights.CLEAN_SHEET_BONUS) == {"GK", "DEF", "MID", "FWD"}


def test_league_logos_cover_all_leagues():
    assert set(config.LEAGUE_LOGOS) == set(config.LEAGUES)
    assert config.LEAGUE_LOGOS["eng.1"].endswith("/23.png")
    assert all(u.startswith("https://a.espncdn.com/") for u in config.LEAGUE_LOGOS.values())


def test_headshot_url_has_id_placeholder():
    assert "{id}" in config.HEADSHOT_URL
    assert config.HEADSHOT_URL.format(id="225607").endswith("/225607.png")
