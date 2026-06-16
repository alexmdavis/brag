def aggregate_club(players):
    """players: list of {"rating": float, "minutes": int}.

    Returns the four club views, each rounded to 2 dp.
    """
    if not players:
        return {"total": 0.0, "average": 0.0, "per90": 0.0, "bestXI": 0.0}

    ratings = [p["rating"] for p in players]
    total = sum(ratings)
    total_minutes = sum(p.get("minutes", 0) for p in players)

    average = total / len(players)
    per90 = (total / (total_minutes / 90)) if total_minutes > 0 else 0.0
    best_xi = sum(sorted(ratings, reverse=True)[:11])

    return {
        "total": round(total, 2),
        "average": round(average, 2),
        "per90": round(per90, 2),
        "bestXI": round(best_xi, 2),
    }
