"""Tests des comparaisons répétées."""

import pytest

from queuesmart.analytics.comparison import (
    compare_scenarios,
    compare_strategies,
    relative_gain,
    replication_seeds,
    run_replications,
)
from queuesmart.analytics.kpi import KpiCalculator
from queuesmart.config import SCENARIOS, ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.strategies import STRATEGIES, build_strategy

REPLICATIONS = 3


def test_seeds_follow_base_seed() -> None:
    assert replication_seeds(10, 3) == [10, 11, 12]
    assert replication_seeds(None, 2) == [None, None]


def test_seeds_require_at_least_one_replication() -> None:
    with pytest.raises(ValueError):
        replication_seeds(1, 0)


def test_run_replications_uses_distinct_seeds(small_config: ScenarioConfig) -> None:
    engine = SimulationEngine(build_strategy("shortest_queue"))
    results = run_replications(engine, small_config, REPLICATIONS)
    assert [result.config.seed for result in results] == [1, 2, 3]


def test_compare_strategies_covers_every_behaviour(small_config: ScenarioConfig) -> None:
    reports = compare_strategies(small_config, KpiCalculator(), REPLICATIONS)
    assert list(reports) == list(STRATEGIES)
    assert reports["least_wait"].mean_wait <= reports["shortest_queue"].mean_wait


def test_compare_scenarios_orders_by_load() -> None:
    reports = compare_scenarios(SCENARIOS, "shortest_queue", KpiCalculator(), REPLICATIONS)
    assert list(reports) == list(SCENARIOS)
    assert reports["Heures creuses"].customer_count == 50 * REPLICATIONS


@pytest.mark.parametrize(
    ("reference", "improved", "expected"), [(4.0, 3.0, 0.25), (2.0, 2.0, 0.0), (0.0, 1.0, 0.0)]
)
def test_relative_gain(reference: float, improved: float, expected: float) -> None:
    assert relative_gain(reference, improved) == pytest.approx(expected)
