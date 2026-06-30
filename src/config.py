BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
# Standings live under a different path prefix (apis/v2, not apis/site/v2) and are
# season-accurate (unlike /teams, which is stale for some leagues).
STANDINGS_BASE = "https://site.api.espn.com/apis/v2/sports/soccer"
WC_LEAGUE = "fifa.world"
SEASON = 2025  # 2025-26 season; domestic roster endpoints return empty without this

LEAGUES = {
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "ger.1": "Bundesliga",
    "usa.1": "MLS",
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
    "usa.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/19.png",
}

# Player headshot URL template (partial coverage; frontend falls back to flag/initials).
HEADSHOT_URL = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

# Second-tier league code per top flight (where promoted clubs' 2025-26 squads
# live). A league appears here only if it has promotion/relegation; its presence
# is what enables the relegation diff in mapping.build_mapping. MLS (usa.1) has
# no pro/rel, so it is intentionally omitted from this map and PROMOTED_2026.
SECOND_TIER = {
    "eng.1": "eng.2", "esp.1": "esp.2", "ita.1": "ita.2",
    "fra.1": "fra.2", "ger.1": "ger.2",
}

# Clubs promoted INTO the upcoming 2026-27 season (ESPN team ids). Their 2025-26
# squads are fetched from the second tier (SECOND_TIER). ESPN had not published
# 2026-27 tables for eng.1/esp.1/ger.1 when this was set, so those are listed
# explicitly; ita.1/fra.1 were derivable but are pinned here for consistency.
PROMOTED_2026 = {
    "eng.1": ["388", "373", "306"],        # Coventry City, Ipswich Town, Hull City
    "esp.1": ["87", "90"],                 # Racing Santander, Deportivo La Coruña
    "ita.1": ["4007", "4057", "17530"],    # Monza, Frosinone, Venezia
    "fra.1": ["170", "2697"],              # Troyes, Le Mans
    "ger.1": ["133", "10388", "3307"],     # Schalke 04, Elversberg, Paderborn
}
