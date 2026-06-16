from src import config
from src.espn_client import fetch_json


def teams_url(league):
    return f"{config.BASE}/{league}/teams"


def roster_url(league, team_id):
    return f"{config.BASE}/{league}/teams/{team_id}/roster?season={config.SEASON}"


def _league_teams(payload):
    return payload["sports"][0]["leagues"][0]["teams"]


def build_mapping(fetch=fetch_json, leagues=None):
    """Return {athleteId: {club, league, leagueName, position}}.

    Skips any club whose roster fetch fails (fail-soft).
    """
    leagues = leagues if leagues is not None else config.LEAGUES
    mapping = {}
    for league, league_name in leagues.items():
        try:
            teams = _league_teams(fetch(teams_url(league)))
        except Exception:
            continue
        for entry in teams:
            team_id = entry["team"]["id"]
            try:
                roster = fetch(roster_url(league, team_id))
            except Exception:
                continue
            club = roster.get("team", {}).get("displayName") or entry["team"].get("displayName")
            club_logo = roster.get("team", {}).get("logo")
            for ath in roster.get("athletes", []):
                aid = ath.get("id")
                if not aid:
                    continue
                mapping[aid] = {
                    "club": club,
                    "league": league,
                    "leagueName": league_name,
                    "position": (ath.get("position", {}) or {}).get("abbreviation"),
                    "clubLogo": club_logo,
                }
    return mapping
