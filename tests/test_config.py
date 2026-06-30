from src import config, weights


def test_leagues_are_big_five_plus_mls():
    assert set(config.LEAGUES) == {"eng.1", "esp.1", "ita.1", "fra.1", "ger.1", "usa.1"}
    assert config.LEAGUES["eng.1"] == "Premier League"
    assert config.LEAGUES["usa.1"] == "MLS"


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
    assert config.LEAGUE_LOGOS["usa.1"].endswith("/19.png")   # MLS league logo
    assert all(u.startswith("https://a.espncdn.com/") for u in config.LEAGUE_LOGOS.values())


def test_pro_rel_config_excludes_mls_and_stays_within_leagues():
    # MLS has no promotion/relegation, so it must appear in neither map; and the
    # pro/rel maps must only ever reference configured leagues.
    assert "usa.1" not in config.SECOND_TIER
    assert "usa.1" not in config.PROMOTED_2026
    assert set(config.SECOND_TIER) <= set(config.LEAGUES)
    assert set(config.PROMOTED_2026) <= set(config.LEAGUES)


def test_headshot_url_has_id_placeholder():
    assert "{id}" in config.HEADSHOT_URL
    assert config.HEADSHOT_URL.format(id="225607").endswith("/225607.png")
