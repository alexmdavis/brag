# Map ESPN domestic-roster position abbreviation -> rating group.
POSITION_GROUPS = {"G": "GK", "D": "DEF", "M": "MID", "F": "FWD"}

# Points per unit of each accumulated WC stat field, by position group.
# Field names are the exact ESPN per-player stat names.
WEIGHTS = {
    "GK": {
        "totalGoals": 6.0, "goalAssists": 4.0, "shotsOnTarget": 0.5,
        "saves": 1.0, "goalsConceded": -1.0,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
        "foulsCommitted": -0.1,
    },
    "DEF": {
        "totalGoals": 6.0, "goalAssists": 4.0, "shotsOnTarget": 0.5,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
        "foulsCommitted": -0.1,
    },
    "MID": {
        "totalGoals": 5.0, "goalAssists": 4.0, "shotsOnTarget": 0.7,
        "totalShots": 0.1,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
        "foulsCommitted": -0.1,
    },
    "FWD": {
        "totalGoals": 4.0, "goalAssists": 3.0, "shotsOnTarget": 1.0,
        "totalShots": 0.2,
        "yellowCards": -1.0, "redCards": -3.0, "ownGoals": -4.0,
    },
}

# Bonus per clean sheet (a match the player featured in where his team conceded 0).
CLEAN_SHEET_BONUS = {"GK": 4.0, "DEF": 4.0, "MID": 1.0, "FWD": 0.0}

# Small floor so simply featuring counts for something.
APPEARANCE_POINTS = 0.5

# Human-readable labels for breakdown components.
FIELD_LABELS = {
    "totalGoals": "Goals", "goalAssists": "Assists", "shotsOnTarget": "Shots on target",
    "totalShots": "Shots", "saves": "Saves", "goalsConceded": "Goals conceded",
    "yellowCards": "Yellow cards", "redCards": "Red cards", "ownGoals": "Own goals",
    "foulsCommitted": "Fouls committed",
}
