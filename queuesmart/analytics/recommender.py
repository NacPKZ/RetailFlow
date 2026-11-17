"""Recommandation du nombre de caisses à ouvrir."""

from dataclasses import dataclass, field

from queuesmart.analytics.comparison import evaluate
from queuesmart.analytics.kpi import KpiCalculator, KpiReport
from queuesmart.config import (
    DEFAULT_REPLICATIONS,
    MAX_REGISTERS,
    MAX_SHARE_OVER_THRESHOLD,
    MIN_REGISTERS,
    WAIT_THRESHOLD_MIN,
    ScenarioConfig,
)
from queuesmart.simulation.engine import SimulationEngine


@dataclass(frozen=True)
class ServiceTarget:
    """Objectif de qualité de service fixé par le responsable du magasin."""

    max_p90_wait_min: float = WAIT_THRESHOLD_MIN
    max_share_over_threshold: float = MAX_SHARE_OVER_THRESHOLD

    def is_met_by(self, report: KpiReport) -> bool:
        """9 clients sur 10 attendent peu ET peu de clients dépassent le seuil."""
        return (
            report.p90_wait <= self.max_p90_wait_min
            and report.share_over_threshold <= self.max_share_over_threshold
        )


@dataclass(frozen=True)
class Recommendation:
    """Nombre de caisses conseillé et KPI obtenus pour chaque nombre testé."""

    recommended_registers: int | None  # None : aucun nombre de caisses ne suffit
    reports_by_register_count: dict[int, KpiReport] = field(repr=False)
    target: ServiceTarget


class RegisterRecommender:
    """Teste chaque nombre de caisses et retient le plus petit qui atteint la cible.

    Le plus petit, car chaque caisse ouverte coûte du personnel.
    """

    def __init__(
        self,
        engine: SimulationEngine,
        calculator: KpiCalculator,
        target: ServiceTarget,
        replications: int = DEFAULT_REPLICATIONS,
    ) -> None:
        self._engine = engine
        self._calculator = calculator
        self._target = target
        self._replications = replications

    def recommend(self, base: ScenarioConfig) -> Recommendation:
        """Recommandation pour le scénario ``base`` (son nombre de caisses est ignoré)."""
        reports = {
            count: self._evaluate(base.with_registers(count))
            for count in range(MIN_REGISTERS, MAX_REGISTERS + 1)
        }
        recommended = next(
            (count for count, report in reports.items() if self._target.is_met_by(report)), None
        )
        return Recommendation(recommended, reports, self._target)

    def _evaluate(self, config: ScenarioConfig) -> KpiReport:
        return evaluate(self._engine, config, self._calculator, self._replications)
