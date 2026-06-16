import json
import os
from datetime import datetime, timezone

from src import config, weights
from src.methodology import build_methodology
from src.rating import rate_player
from src.aggregate import aggregate_club
from src.mapping import build_mapping
from src.wc_stats import accumulate_players

DEFAULT_OUTPUT = os.path.join("web", "standings.json")


def assemble_standings(records, generated_at):
    """Build the full standings dict from accumulated player records."""
    clubs = {}
    for rec in records.values():
        rated = rate_player(rec)
        player = {
            "id": rec["id"], "name": rec["name"], "position": rec["position"],
            "nation": rec["nation"], "nationFlag": rec.get("nationFlag"),
            "headshot": rec.get("headshot"), "minutes": rec["minutes"],
            "rating": rated["rating"], "breakdown": rated["breakdown"],
        }
        club = clubs.setdefault(rec["club"], {
            "club": rec["club"], "league": rec["league"],
            "leagueName": rec["leagueName"],
            "clubLogo": rec.get("clubLogo"),
            "leagueLogo": config.LEAGUE_LOGOS.get(rec["league"]),
            "players": [],
        })
        club["players"].append(player)

    club_list = []
    for club in clubs.values():
        club["players"].sort(key=lambda p: p["rating"], reverse=True)
        club["scores"] = aggregate_club(club["players"])
        club["playerCount"] = len(club["players"])
        club_list.append(club)

    club_list.sort(key=lambda c: c["scores"]["total"], reverse=True)

    return {
        "generatedAt": generated_at,
        "season": config.SEASON,
        "tournament": config.WC_LEAGUE,
        "coverage": {"playersMapped": len(records),
                     "clubs": len(club_list)},
        "methodology": build_methodology(weights),
        "clubs": club_list,
    }


def write_standings(standings, path=DEFAULT_OUTPUT):
    """Atomic write, but only if coverage is non-empty. Returns True if written."""
    if standings["coverage"]["playersMapped"] <= 0:
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(standings, f, indent=2)
    os.replace(tmp, path)
    return True


def main(fetch=None, path=DEFAULT_OUTPUT):
    from src.espn_client import fetch_json
    fetch = fetch or fetch_json
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mapping = build_mapping(fetch=fetch)
    records = accumulate_players(mapping, fetch=fetch)
    standings = assemble_standings(records, generated_at=generated_at)
    written = write_standings(standings, path=path)
    print(f"mapped={standings['coverage']['playersMapped']} "
          f"clubs={standings['coverage']['clubs']} written={written}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
