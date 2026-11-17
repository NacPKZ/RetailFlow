"""Comparaisons répétées : plusieurs graines, plusieurs comportements, plusieurs scénarios.

Une seule simulation dépend beaucoup du hasard ; on compare donc des KPI
calculés sur ``replications`` simulations (graines seed, seed + 1, …).
"""

from collections.abc import Mapping

from queuesmart.analytics.kpi import KpiCalculator, KpiReport
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import STRATEGIES, build_strategy


def replication_seeds(seed: int | None, replications: int) -> list[int | None]:
    """Graines successives à partir de ``seed`` (``None`` : tirages non reproductibles)."""
    if replications < 1:
        raise ValueError("Il faut au moins une réplication.")
    if seed is None:
        return [None] * replications
    return [seed + offset for offset in range(replications)]


def run_replications(
    engine: SimulationEngine, config: ScenarioConfig, replications: int
) -> list[SimulationResult]:
    """Simule le même scénario avec ``replications`` graines différentes."""
    seeds = replication_seeds(config.seed, replications)
    return [engine.run(config.with_seed(seed)) for seed in seeds]


def evaluate(
    engine: SimulationEngine,
    config: ScenarioConfig,
    calculator: KpiCalculator,
    replications: int,
) -> KpiReport:
    """KPI regroupés de plusieurs réplications d'un scénario."""
    return calculator.compute_many(run_replications(engine, config, replications))


def compare_strategies(
    config: ScenarioConfig, calculator: KpiCalculator, replications: int
) -> dict[str, KpiReport]:
    """KPI de chaque comportement client sur le même scénario (mêmes graines)."""
    return {
        name: evaluate(SimulationEngine(build_strategy(name)), config, calculator, replications)
        for name in STRATEGIES
    }


def compare_scenarios(
    scenarios: Mapping[str, ScenarioConfig],
    strategy_name: str,
    calculator: KpiCalculator,
    replications: int,
) -> dict[str, KpiReport]:
    """KPI de chaque scénario pour un même comportement client."""
    engine = SimulationEngine(build_strategy(strategy_name))
    return {
        name: evaluate(engine, config, calculator, replications)
        for name, config in scenarios.items()
    }


def relative_gain(reference: float, improved: float) -> float:
    """Gain relatif (0.25 = 25 % de moins). Nul si la référence vaut 0."""
    if reference == 0:
        return 0.0
    return (reference - improved) / reference
