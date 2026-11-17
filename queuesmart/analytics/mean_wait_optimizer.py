"""Optimisation selon l'attente moyenne, sans casser l'optimiseur historique."""

from dataclasses import dataclass

from queuesmart.analytics.kpi import KpiCalculator, KpiReport
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine


@dataclass(frozen=True)
class MeanWaitRecommendation:
    recommended_registers: int | None
    mean_wait_by_register_count: dict[int, float]
    threshold_min: float


def recommend_by_mean_wait(
    engine: SimulationEngine,
    calculator: KpiCalculator,
    config: ScenarioConfig,
    threshold_min: float,
    max_registers: int = 5,
) -> MeanWaitRecommendation:
    """Choisit la plus petite configuration conforme, à graine identique.

    Un seul tirage par configuration : résultat reproductible, mais non robuste
    statistiquement. Une version multi-réplications pourra être ajoutée ensuite.
    """
    if threshold_min < 0:
        raise ValueError("Le seuil doit être positif ou nul")
    if not 1 <= max_registers <= 5:
        raise ValueError("Le maximum de caisses doit être compris entre 1 et 5")
    waits = {
        n: calculator.compute(engine.run(config.with_registers(n))).mean_wait
        for n in range(1, max_registers + 1)
    }
    recommended = next((n for n, wait in waits.items() if wait <= threshold_min), None)
    return MeanWaitRecommendation(recommended, waits, threshold_min)
