"""Tests de la cible de service et de la recommandation du nombre de caisses."""

import pytest

from queuesmart.analytics.kpi import KpiCalculator, KpiReport
from queuesmart.analytics.recommender import RegisterRecommender, ServiceTarget
from queuesmart.config import MAX_REGISTERS, MIN_REGISTERS, SCENARIOS, ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.strategies import build_strategy


def report(p90_wait: float, share_over_threshold: float) -> KpiReport:
    return KpiReport(10, 1.0, 1.0, p90_wait, 9.0, share_over_threshold, 0.5, {1: 0.5})


@pytest.mark.parametrize(
    ("p90", "share", "expected"),
    [(4.0, 0.05, True), (5.0, 0.10, True), (5.1, 0.05, False), (4.0, 0.11, False)],
)
def test_target_requires_both_conditions(p90: float, share: float, expected: bool) -> None:
    assert ServiceTarget().is_met_by(report(p90, share)) is expected


def recommender(target: ServiceTarget, replications: int = 20) -> RegisterRecommender:
    engine = SimulationEngine(build_strategy("shortest_queue"))
    return RegisterRecommender(engine, KpiCalculator(), target, replications)


@pytest.fixture(scope="module")
def recommendations() -> dict[str, int | None]:
    advisor = recommender(ServiceTarget())
    return {
        name: advisor.recommend(config).recommended_registers
        for name, config in SCENARIOS.items()
    }


def test_recommendation_grows_with_load(recommendations: dict[str, int | None]) -> None:
    counts = list(recommendations.values())
    assert None not in counts
    assert counts == sorted(counts)


def test_expected_register_counts(recommendations: dict[str, int | None]) -> None:
    assert recommendations["Heures creuses"] in (2, 3)
    assert recommendations["Heures normales"] == 4
    assert recommendations["Heure de pointe"] == 6


def test_every_register_count_is_evaluated() -> None:
    advisor = recommender(ServiceTarget(), replications=2)
    recommendation = advisor.recommend(SCENARIOS["Heures creuses"])
    expected = list(range(MIN_REGISTERS, MAX_REGISTERS + 1))
    assert list(recommendation.reports_by_register_count) == expected


def test_unreachable_target_gives_none() -> None:
    overloaded = ScenarioConfig("Saturé", 300, 10.0, 3.0, 1)
    recommendation = recommender(ServiceTarget(), replications=2).recommend(overloaded)
    assert recommendation.recommended_registers is None
    assert recommendation.target == ServiceTarget()
