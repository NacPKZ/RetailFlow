"""Tests du plan du magasin (logique pure de l'animation 2D)."""

import pytest

from queuesmart.config import SCENARIOS
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import build_strategy
from queuesmart.ui.store_layout import (
    ANIMATION_STEP_MIN,
    MAX_FRAMES,
    QUEUE_SPACING,
    SERVING,
    WAIT_CRITICAL,
    WAIT_OK,
    WAIT_WARNING,
    WAITING,
    PlacedCustomer,
    StoreLayout,
    animation_step,
    describe_status,
    wait_level,
)
from tests.builders import build_result


@pytest.fixture
def result() -> SimulationResult:
    # À t = 2,5 :
    #   caisse 1 : client 1 servi (0 -> 4), puis clients 2 (arrivé à 1) et 4 (arrivé à 2) en file ;
    #   caisse 2 : client 3 servi (1 -> 3).
    return build_result(
        [(0.0, 4.0, 1), (1.0, 2.0, 1), (1.0, 2.0, 2), (2.0, 1.0, 1)], register_count=2
    )


def placed_by_id(result: SimulationResult, time: float) -> dict[int, PlacedCustomer]:
    layout = StoreLayout(result.config.open_registers)
    return {p.customer_id: p for p in layout.place_customers(result.snapshot_at(time), result)}


def test_registers_are_aligned_and_distinct() -> None:
    layout = StoreLayout(4)
    positions = [layout.register_position(register_id) for register_id in range(1, 5)]
    assert len(set(positions)) == 4
    assert len({y for _, y in positions}) == 1


@pytest.mark.parametrize("register_id", [0, 3])
def test_unknown_register_position_is_rejected(register_id: int) -> None:
    with pytest.raises(ValueError):
        StoreLayout(2).register_position(register_id)


def test_layout_needs_a_register() -> None:
    with pytest.raises(ValueError):
        StoreLayout(0)


def test_one_point_per_present_customer(result: SimulationResult) -> None:
    snapshot = result.snapshot_at(2.5)
    placed = StoreLayout(2).place_customers(snapshot, result)
    present = sum(register.queue_length for register in snapshot.registers)
    assert len(placed) == present == 4
    assert len({(p.x, p.y) for p in placed}) == len(placed)


def test_serving_customer_is_at_register(result: SimulationResult) -> None:
    served = placed_by_id(result, 2.5)[1]
    assert served.state == SERVING
    assert (served.x, served.y) == StoreLayout(2).register_position(1)
    assert served.wait_so_far == 0.0


def test_waiting_customers_follow_queue_order(result: SimulationResult) -> None:
    placed = placed_by_id(result, 2.5)
    second, fourth = placed[2], placed[4]
    assert second.state == fourth.state == WAITING
    assert second.x == fourth.x
    assert fourth.y == second.y - QUEUE_SPACING
    assert second.wait_so_far == pytest.approx(1.5)


def test_full_simulation_points_match_presence() -> None:
    result = SimulationEngine(build_strategy("least_wait")).run(SCENARIOS["Heure de pointe"])
    layout = StoreLayout(result.config.open_registers)
    for snapshot in result.timeline(step_min=5.0):
        present = sum(register.queue_length for register in snapshot.registers)
        assert len(layout.place_customers(snapshot, result)) == present


@pytest.mark.parametrize(
    ("wait", "expected"),
    [
        (0.0, WAIT_OK),
        (2.5, WAIT_OK),
        (2.6, WAIT_WARNING),
        (5.0, WAIT_WARNING),
        (5.1, WAIT_CRITICAL),
    ],
)
def test_wait_level(wait: float, expected: str) -> None:
    assert wait_level(wait) == expected


def test_animation_step_is_constant_for_normal_simulations() -> None:
    assert animation_step(65.0) == ANIMATION_STEP_MIN


def test_animation_step_caps_frame_count() -> None:
    assert animation_step(5000.0) * MAX_FRAMES == pytest.approx(5000.0)


@pytest.mark.parametrize(
    ("time", "expected"),
    [(0.5, "pas encore arrivé"), (2.5, "en file depuis 1 min 30 s"),
     (5.0, "en caisse 1 (a attendu 3 min)"), (7.0, "parti (a attendu 3 min)")],
)
def test_describe_status(result: SimulationResult, time: float, expected: str) -> None:
    assert describe_status(result.customer(2), time) == expected
