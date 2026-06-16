import re


def parse_minute(clock_display):
    """'61\\'' -> 61, '45\\'+2' -> 45, '' -> 0."""
    if not clock_display:
        return 0
    m = re.match(r"\s*(\d+)", clock_display)
    minute = int(m.group(1)) if m else 0
    return min(minute, 90)


def parse_sub_events(key_events):
    """Return [{'minute': int, 'ids': set(athlete_id)}] for Substitution events."""
    out = []
    for e in key_events or []:
        if (e.get("type", {}) or {}).get("text") != "Substitution":
            continue
        minute = parse_minute((e.get("clock", {}) or {}).get("displayValue"))
        ids = {
            (p.get("athlete", {}) or {}).get("id")
            for p in e.get("participants", []) or []
            if (p.get("athlete", {}) or {}).get("id")
        }
        out.append({"minute": minute, "ids": ids})
    return out


def _sub_minute_for(player_id, sub_events):
    for s in sub_events:
        if player_id in s["ids"]:
            return s["minute"]
    return None


def compute_minutes(player, sub_events):
    """Minutes in [0, 90] from roster booleans + matched Substitution events."""
    pid = (player.get("athlete", {}) or {}).get("id")
    starter = bool(player.get("starter"))
    subbed_in = bool(player.get("subbedIn"))
    subbed_out = bool(player.get("subbedOut"))
    minute = _sub_minute_for(pid, sub_events)

    if starter and not subbed_out:
        return 90
    if starter and subbed_out:
        return minute if minute is not None else 90
    if subbed_in:
        return max(1, 90 - minute) if minute is not None else 15
    return 0
