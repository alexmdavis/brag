from src.weights import (
    POSITION_GROUPS, WEIGHTS, CLEAN_SHEET_BONUS, APPEARANCE_POINTS, FIELD_LABELS,
)


def position_group(abbreviation):
    """Map a domestic-roster position abbreviation to a rating group."""
    return POSITION_GROUPS.get(abbreviation, "MID")


def rate_player(record):
    """record: {"position": str, "stats": {field: number}, "cleanSheets": int}

    Returns {"rating": float, "breakdown": [{"label": str, "points": float}]}.
    """
    group = position_group(record.get("position"))
    stats = record.get("stats", {})
    components = []

    for field, weight in WEIGHTS[group].items():
        value = stats.get(field, 0) or 0
        points = round(value * weight, 2)
        if points != 0:
            components.append({"label": FIELD_LABELS.get(field, field), "points": points})

    clean_sheets = record.get("cleanSheets", 0) or 0
    cs_points = round(clean_sheets * CLEAN_SHEET_BONUS[group], 2)
    if cs_points != 0:
        components.append({"label": "Clean sheets", "points": cs_points})

    appearances = stats.get("appearances", 0) or 0
    app_points = round(appearances * APPEARANCE_POINTS, 2)
    if app_points != 0:
        components.append({"label": "Appearances", "points": app_points})

    rating = round(sum(c["points"] for c in components), 2)
    return {"rating": rating, "breakdown": components}
