"""Download a small set of real ESPN responses for offline tests.

Run once: python3 tests/capture_fixtures.py
"""
import json
import os
import sys

# Allow running directly (python3 tests/capture_fixtures.py) by putting repo root on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.espn_client import fetch_json

OUT = os.path.join(os.path.dirname(__file__), "fixtures")


def save(name, payload):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(payload, f)
    print("wrote", name)


def main():
    # One Serie A team roster (mapping shape).
    save("ita1_teams.json", fetch_json(f"{config.BASE}/ita.1/teams"))
    save("ita1_team103_roster.json",
         fetch_json(f"{config.BASE}/ita.1/teams/103/roster?season={config.SEASON}"))
    # One completed WC match summary (stats shape).
    save("wc_summary_760416.json",
         fetch_json(f"{config.BASE}/{config.WC_LEAGUE}/summary?event=760416"))


if __name__ == "__main__":
    main()
