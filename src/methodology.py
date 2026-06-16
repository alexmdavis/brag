def build_methodology(weights):
    """Turn the weights module into a JSON-serializable methodology dict.

    Pure: returns copies so the caller can't mutate the source of truth.
    """
    views = [
        {"key": "total", "label": "Total",
         "formula": "Sum of every player's rating for the club."},
        {"key": "average", "label": "Average",
         "formula": "Mean rating across the club's World Cup players."},
        {"key": "per90", "label": "Per-90",
         "formula": "Total rating divided by (total minutes / 90)."},
        {"key": "bestXI", "label": "Best XI",
         "formula": "Sum of the club's top 11 player ratings."},
    ]
    notes = [
        "Players are attributed to their 2025–26 club.",
        "Stats come from completed or in-progress World Cup matches via ESPN.",
        "A clean sheet = a match the player featured in where his team conceded 0 goals.",
        "A small appearance bonus rewards simply featuring.",
    ]
    return {
        "positionGroups": dict(weights.POSITION_GROUPS),
        "weights": {group: dict(fields) for group, fields in weights.WEIGHTS.items()},
        "cleanSheetBonus": dict(weights.CLEAN_SHEET_BONUS),
        "appearancePoints": weights.APPEARANCE_POINTS,
        "fieldLabels": dict(weights.FIELD_LABELS),
        "views": views,
        "notes": notes,
    }
