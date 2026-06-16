from src import config
from src.espn_client import fetch_json


def teams_url(league):
    return f"{config.BASE}/{league}/teams"


def roster_url(league, team_id):
    return f"{config.BASE}/{league}/teams/{team_id}/roster?season={config.SEASON}"


def standings_url(league, season):
    return f"{config.STANDINGS_BASE}/{league}/standings?season={season}"


def standings_entries(payload):
    """Flatten a standings payload to its list of team entries."""
    out = []
    for child in payload.get("children", []) or []:
        out += (child.get("standings", {}) or {}).get("entries", []) or []
    return out


def _relegated_ids(fetch, league, season, current):
    """Ids of clubs leaving after `season`.

    Prefer diffing the upcoming season's membership (accurate where ESPN has
    published it); otherwise fall back to the standings "Relegation" note.
    """
    try:
        nxt = standings_entries(fetch(standings_url(league, season + 1)))
    except Exception:
        nxt = []
    if nxt:
        nxt_ids = {e["team"]["id"] for e in nxt}
        return {e["team"]["id"] for e in current
                if e.get("team", {}).get("id") not in nxt_ids}
    return {e["team"]["id"] for e in current
            if (e.get("note") or {}).get("description") == "Relegation"}


def _add_club(mapping, fetch, url, fallback_team, league, league_name, promoted, relegated):
    """Fetch one club's roster and add its athletes to the mapping (fail-soft)."""
    try:
        roster = fetch(url)
    except Exception:
        return
    club = roster.get("team", {}).get("displayName") or fallback_team.get("displayName")
    club_logo = (roster.get("team", {}).get("logo")
                 or (fallback_team.get("logos") or [{}])[0].get("href"))
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
            "promoted": promoted,
            "relegated": relegated,
        }


def build_mapping(fetch=fetch_json, leagues=None, season=None,
                  promoted_map=None, second_tier=None):
    """Return {athleteId: {club, league, leagueName, position, clubLogo,
    promoted, relegated}}.

    The board's clubs are the 2025-26 top flight (from season-accurate standings)
    plus the clubs promoted INTO the upcoming season, whose 2025-26 squads are
    pulled from the second tier. `relegated` = leaving after this season;
    `promoted` = joining for the next one. Fail-soft per league and per club.
    """
    leagues = leagues if leagues is not None else config.LEAGUES
    season = season if season is not None else config.SEASON
    promoted_map = promoted_map if promoted_map is not None else config.PROMOTED_2026
    second_tier = second_tier if second_tier is not None else config.SECOND_TIER

    mapping = {}
    for league, league_name in leagues.items():
        # Top-flight clubs for the season the board covers (established + relegated).
        try:
            current = standings_entries(fetch(standings_url(league, season)))
        except Exception:
            current = []
        relegated_ids = _relegated_ids(fetch, league, season, current) if current else set()
        for entry in current:
            team = entry.get("team", {})
            tid = team.get("id")
            if not tid:
                continue
            _add_club(mapping, fetch, roster_url(league, tid), team, league, league_name,
                      promoted=False, relegated=(tid in relegated_ids))

        # Clubs promoted into the upcoming season, mapped from their second-tier squads.
        tier2 = second_tier.get(league)
        if tier2:
            for tid in promoted_map.get(league, []):
                _add_club(mapping, fetch, roster_url(tier2, tid), {"id": tid},
                          league, league_name, promoted=True, relegated=False)
    return mapping
