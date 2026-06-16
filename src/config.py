BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
WC_LEAGUE = "fifa.world"
SEASON = 2025  # 2025-26 season; domestic roster endpoints return empty without this

LEAGUES = {
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "ger.1": "Bundesliga",
}

# Inclusive YYYYMMDD range to scan the WC scoreboard for event IDs.
TOURNAMENT_START = "20260611"
TOURNAMENT_END = "20260719"

# ESPN CDN league-logo URLs (verified HTTP 200, keyed by league code).
LEAGUE_LOGOS = {
    "eng.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png",
    "esp.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png",
    "ita.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png",
    "fra.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png",
    "ger.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png",
}

# Player headshot URL template (partial coverage; frontend falls back to flag/initials).
HEADSHOT_URL = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"
