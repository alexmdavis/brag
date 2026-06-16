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
