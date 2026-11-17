"""Tests du résultat de simulation et des snapshots.

Cas construit à la main (2 caisses) :
    client 1 : arrive à 0, dure 4, caisse 1 -> servi de 0 à 4
    client 2 : arrive à 1, dure 2, caisse 1 -> servi de 4 à 6
    client 3 : arrive à 2, dure 1, caisse 2 -> servi de 2 à 3
"""

import pytest

from queuesmart.exceptions import UnknownCustomerError
from queuesmart.simulation.result import SimulationResult
from tests.builders import build_result


@pytest.fixture
def result() -> SimulationResult:
    return build_result([(0.0, 4.0, 1), (1.0, 2.0, 1), (2.0, 1.0, 2)], register_count=2)


def test_end_time_is_last_departure(result: SimulationResult) -> None:
    assert result.end_time == 6.0


def test_customer_lookup(result: SimulationResult) -> None:
    assert result.customer(2).wait_time == 3.0


def test_unknown_customer_raises_business_error(result: SimulationResult) -> None:
    with pytest.raises(UnknownCustomerError):
        result.customer(99)


def test_snapshot_describes_each_register(result: SimulationResult) -> None:
    snapshot = result.snapshot_at(2.5)
    first, second = snapshot.registers
    assert (first.serving_customer_id, first.waiting_customer_ids) == (1, (2,))
    assert first.queue_length == 2
    assert first.estimated_wait == pytest.approx(3.5)
    assert (second.serving_customer_id, second.waiting_customer_ids) == (3, ())
    assert (snapshot.not_arrived_count, snapshot.departed_count) == (0, 0)


def test_snapshot_counts_arrivals_and_departures(result: SimulationResult) -> None:
    snapshot = result.snapshot_at(0.5)
    assert (snapshot.not_arrived_count, snapshot.departed_count) == (2, 0)
    assert result.snapshot_at(6.0).departed_count == 3


def test_empty_register_snapshot(result: SimulationResult) -> None:
    second = result.snapshot_at(0.5).registers[1]
    assert second.serving_customer_id is None
    assert second.queue_length == 0
    assert second.estimated_wait == 0.0


def test_timeline_covers_whole_simulation(result: SimulationResult) -> None:
    times = [snapshot.time for snapshot in result.timeline(step_min=2.5)]
    assert times == [0.0, 2.5, 5.0, 6.0]


@pytest.mark.parametrize("step", [0.0, -1.0])
def test_timeline_rejects_non_positive_step(result: SimulationResult, step: float) -> None:
    with pytest.raises(ValueError):
        result.timeline(step)
