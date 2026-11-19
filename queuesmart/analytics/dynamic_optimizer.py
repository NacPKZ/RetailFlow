"""Règle de recommandation fondée sur l'attente moyenne des clients servis."""

from __future__ import annotations

from dataclasses import dataclass

from queuesmart.analytics.dynamic_comparison import DynamicComparisonReport


@dataclass(frozen=True)
class DynamicRecommendation:
    recommended_registers: int | None
    threshold_min: float
    mean_wait_by_register_count: dict[int, float | None]
    message: str


def recommend_by_mean_wait(
    comparison: DynamicComparisonReport,
    threshold_min: float,
) -> DynamicRecommendation:
    """Retient le plus petit n dont l'attente moyenne des servis respecte le seuil."""
    if threshold_min < 0:
        raise ValueError("Le seuil d'attente doit être positif ou nul.")

    waits = {
        row.register_count: row.mean_wait_served_min
        for row in comparison.rows
    }
    recommended = next(
        (
            register_count
            for register_count, mean_wait in waits.items()
            if mean_wait is not None and mean_wait <= threshold_min
        ),
        None,
    )
    message = (
        f"{recommended} caisse(s) : première configuration respectant le seuil."
        if recommended is not None
        else "aucune configuration conforme"
    )
    return DynamicRecommendation(recommended, threshold_min, waits, message)
