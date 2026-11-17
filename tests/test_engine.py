"""Tests du moteur : invariants métier sur tous les scénarios et comportements."""

import itertools

import pytest

from queuesmart.config import SCENARIOS, ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import STRATEGIES, build_strategy

CASES = list(itertools.product(SCENARIOS.values(), STRATEGIES))


def simulate(config: ScenarioConfig, strategy_name: str) -> SimulationResult:
    return SimulationEngine(build_strategy(strategy_name)).run(config)


@pytest.fixture(params=CASES, ids=lambda case: f"{case[0].name}-{case[1]}")
def result(request) -> SimulationResult:
    return simulate(*request.param)


def test_everyone_is_served(result: SimulationResult) -> None:
    assert len(result.customers) == result.config.customer_count
    assert all(customer.is_served for customer in result.customers)


def test_no_service_before_arrival(result: SimulationResult) -> None:
    assert all(customer.wait_time >= 0 for customer in result.customers)


def test_no_overlap_on_a_register(result: SimulationResult) -> None:
    for register in result.registers:
        for previous, current in itertools.pairwise(register.customers):
            assert current.service_start >= previous.service_end


def test_registers_match_config(result: SimulationResult) -> None:
    ids = [register.register_id for register in result.registers]
    assert ids == list(range(1, result.config.open_registers + 1))
    served = sum(len(register.customers) for register in result.registers)
    assert served == result.config.customer_count


def test_population_is_conserved_over_time(result: SimulationResult) -> None:
    for snapshot in result.timeline(step_min=1.0):
        present = sum(register.queue_length for register in snapshot.registers)
        total = snapshot.not_arrived_count + present + snapshot.departed_count
        assert total == result.config.customer_count


def test_engine_exposes_its_strategy_and_names_result() -> None:
    engine = SimulationEngine(build_strategy("least_wait"))
    assert engine.strategy.name == "least_wait"
    assert engine.run(SCENARIOS["Heures creuses"]).strategy_name == "least_wait"


def test_same_seed_gives_same_result() -> None:
    config = SCENARIOS["Heures normales"]
    first, second = simulate(config, "shortest_queue"), simulate(config, "shortest_queue")
    assert [c.wait_time for c in first.customers] == [c.wait_time for c in second.customers]


def test_screen_reduces_mean_wait_at_peak() -> None:
    config = SCENARIOS["Heure de pointe"]
    waits = {name: simulate(config, name).customers for name in STRATEGIES}
    mean = {name: sum(c.wait_time for c in cs) / len(cs) for name, cs in waits.items()}
    assert mean["least_wait"] <= mean["shortest_queue"]
