from datetime import date, timedelta

from src import config
from src.config import HEADSHOT_URL
from src.espn_client import fetch_json
from src.minutes import parse_sub_events, compute_minutes


def team_goals_conceded(summary):
    """Map team id -> goals conceded (the other competitor's score)."""
    comps = (summary.get("header", {}).get("competitions") or [{}])[0]
    competitors = comps.get("competitors", []) or []
    scores = {}
    for c in competitors:
        tid = (c.get("team", {}) or {}).get("id")
        try:
            scores[tid] = int(c.get("score"))
        except (TypeError, ValueError):
            scores[tid] = 0
    conceded = {}
    total = sum(scores.values())
    for tid, scored in scores.items():
        conceded[tid] = total - scored
    return conceded


def _stats_dict(player):
    return {s.get("name"): (s.get("value") or 0) for s in player.get("stats", []) or []}


def _new_record(pid, player, info, nation, nation_flag):
    return {
        "id": pid,
        "name": player.get("athlete", {}).get("displayName"),
        "nation": nation,
        "nationFlag": nation_flag,
        "headshot": HEADSHOT_URL.format(id=pid),
        "club": info["club"],
        "league": info["league"],
        "leagueName": info["leagueName"],
        "position": info["position"],
        "clubLogo": info.get("clubLogo"),
        "stats": {},
        "minutes": 0,
        "matches": 0,
        "cleanSheets": 0,
    }


def process_match_summary(summary, mapping, acc):
    """Fold one parsed WC match summary into the accumulator `acc` (in place)."""
    subs = parse_sub_events(summary.get("keyEvents"))
    conceded = team_goals_conceded(summary)

    for team in summary.get("rosters", []) or []:
        team_obj = team.get("team", {})
        nation = team_obj.get("displayName")
        team_id = team_obj.get("id")
        nation_flag = (team_obj.get("logos") or [{}])[0].get("href")
        for player in team.get("roster", []) or []:
            pid = (player.get("athlete", {}) or {}).get("id")
            info = mapping.get(pid)
            if not info:
                continue
            featured = bool(player.get("starter")) or bool(player.get("subbedIn"))
            if not featured:
                continue

            rec = acc.get(pid) or _new_record(pid, player, info, nation, nation_flag)
            match_stats = _stats_dict(player)
            for name, value in match_stats.items():
                rec["stats"][name] = rec["stats"].get(name, 0) + value

            minutes = compute_minutes(player, subs)
            rec["minutes"] += minutes
            rec["matches"] += 1
            if conceded.get(team_id, 1) == 0:
                rec["cleanSheets"] += 1
            acc[pid] = rec


def _date_range(start, end):
    d0 = date(int(start[:4]), int(start[4:6]), int(start[6:8]))
    d1 = date(int(end[:4]), int(end[4:6]), int(end[6:8]))
    days = []
    d = d0
    while d <= d1:
        days.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return days


def collect_event_ids(fetch=fetch_json):
    """Completed or in-progress WC event IDs across the tournament date range."""
    ids = []
    for ymd in _date_range(config.TOURNAMENT_START, config.TOURNAMENT_END):
        url = f"{config.BASE}/{config.WC_LEAGUE}/scoreboard?dates={ymd}"
        try:
            board = fetch(url)
        except Exception:
            continue
        for e in board.get("events", []) or []:
            state = (e.get("status", {}).get("type", {}) or {}).get("state")
            if state in ("post", "in"):     # completed or live; skip "pre"
                ids.append(e.get("id"))
    return ids


def accumulate_players(mapping, fetch=fetch_json):
    """Return {athleteId: record} across all played WC matches."""
    acc = {}
    for eid in collect_event_ids(fetch=fetch):
        url = f"{config.BASE}/{config.WC_LEAGUE}/summary?event={eid}"
        try:
            summary = fetch(url)
        except Exception:
            continue
        process_match_summary(summary, mapping, acc)
    return acc
