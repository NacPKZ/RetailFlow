import pytest
from queuesmart.analytics.kpi import KpiCalculator
from queuesmart.analytics.mean_wait_optimizer import recommend_by_mean_wait
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.strategies import build_strategy


def test_mean_wait_recommendation_reproducible():
    engine = SimulationEngine(build_strategy("shortest_queue"))
    config = ScenarioConfig("demo", 30, 30, 2, 2, seed=42)
    a = recommend_by_mean_wait(engine, KpiCalculator(), config, 5)
    b = recommend_by_mean_wait(engine, KpiCalculator(), config, 5)
    assert a == b
    assert list(a.mean_wait_by_register_count) == [1, 2, 3, 4, 5]
    if a.recommended_registers is not None:
        assert a.mean_wait_by_register_count[a.recommended_registers] <= 5
        assert all(a.mean_wait_by_register_count[n] > 5 for n in range(1, a.recommended_registers))


def test_impossible_threshold():
    engine = SimulationEngine(build_strategy("shortest_queue"))
    config = ScenarioConfig("busy", 100, 5, 3, 2, seed=42)
    r = recommend_by_mean_wait(engine, KpiCalculator(), config, 0)
    assert r.recommended_registers is None


def test_invalid_parameters():
    engine = SimulationEngine(build_strategy("shortest_queue"))
    config = ScenarioConfig("demo", 5, 10, 2, 2)
    with pytest.raises(ValueError):
        recommend_by_mean_wait(engine, KpiCalculator(), config, -1)
