"""Diagnostics de simulation avec seuils choisis et définitions explicites."""

from itertools import groupby

import pandas as pd


def saturation_periods(queues: pd.DataFrame, limit: int) -> list[dict]:
    """Intervalles [début, fin[ au-dessus du seuil, client en service exclu."""
    periods = []
    for register, frame in queues.groupby("Caisse"):
        rows = frame.to_dict("records")
        for saturated, group in groupby(
            enumerate(rows), key=lambda item: item[1]["En file"] >= limit
        ):
            if not saturated:
                continue
            span = list(group)
            start = span[0][1]["Minute"]
            end = rows[min(span[-1][0] + 1, len(rows) - 1)]["Minute"]
            if end > start:
                periods.append(
                    {
                        "Caisse": register,
                        "Début (min)": start,
                        "Fin (min)": end,
                        "Pic de file": max(row["En file"] for _, row in span),
                    }
                )
    return periods
