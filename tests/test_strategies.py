"""Tests des comportements clients (stratégies)."""

import pytest

from queuesmart.domain.customer import Customer
from queuesmart.domain.register import CheckoutRegister
from queuesmart.exceptions import UnknownStrategyError
from queuesmart.simulation.strategies import (
    STRATEGIES,
    AssignmentStrategy,
    LeastWaitStrategy,
    ShortestQueueStrategy,
    build_strategy,
)


def register_with(register_id: int, *durations: float) -> CheckoutRegister:
    """Caisse dont tous les clients sont arrivés à t = 0."""
    register = CheckoutRegister(register_id)
    for index, duration in enumerate(durations):
        register.serve(Customer(register_id * 100 + index, 0.0, duration))
    return register


@pytest.fixture
def diverging_registers() -> list[CheckoutRegister]:
    """Caisse 1 : un seul client mais un très gros chariot (10 min).
    Caisse 2 : deux clients rapides (1 min chacun)."""
    return [register_with(1, 10.0), register_with(2, 1.0, 1.0)]


def test_shortest_queue_picks_fewest_customers(diverging_registers) -> None:
    assert ShortestQueueStrategy().choose(diverging_registers, 0.0).register_id == 1


def test_least_wait_picks_lowest_estimated_wait(diverging_registers) -> None:
    assert LeastWaitStrategy().choose(diverging_registers, 0.0).register_id == 2


@pytest.mark.parametrize("strategy_class", [ShortestQueueStrategy, LeastWaitStrategy])
def test_ties_go_to_smallest_register_id(strategy_class: type[AssignmentStrategy]) -> None:
    registers = [register_with(3, 2.0), register_with(1, 2.0), register_with(2, 2.0)]
    assert strategy_class().choose(registers, 0.0).register_id == 1


@pytest.mark.parametrize("strategy_class", [ShortestQueueStrategy, LeastWaitStrategy])
def test_no_register_is_an_error(strategy_class: type[AssignmentStrategy]) -> None:
    with pytest.raises(ValueError):
        strategy_class().choose([], 0.0)


def test_registry_and_builder() -> None:
    assert set(STRATEGIES) == {"shortest_queue", "least_wait"}
    for name in STRATEGIES:
        strategy = build_strategy(name)
        assert strategy.name == name
        assert strategy.label


def test_unknown_strategy_raises_business_error() -> None:
    with pytest.raises(UnknownStrategyError, match="inconnu"):
        build_strategy("au_hasard")
