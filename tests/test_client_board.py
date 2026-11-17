"""Tests du panneau d'affichage client."""

import pytest

from queuesmart.simulation.result import RegisterSnapshot, StoreSnapshot
from queuesmart.ui.client_board import build_board, format_minutes


def snapshot_with_waits(*waits: float) -> StoreSnapshot:
    registers = tuple(
        RegisterSnapshot(register_id, None, (), wait)
        for register_id, wait in enumerate(waits, start=1)
    )
    return StoreSnapshot(time=0.0, registers=registers, not_arrived_count=0, departed_count=0)


def recommended_ids(snapshot: StoreSnapshot) -> list[int]:
    return [line.register_id for line in build_board(snapshot) if line.is_recommended]


def test_one_line_per_register_in_order() -> None:
    board = build_board(snapshot_with_waits(3.0, 1.0, 2.0))
    assert [line.register_id for line in board] == [1, 2, 3]
    assert [line.estimated_wait for line in board] == [3.0, 1.0, 2.0]


def test_recommended_register_has_lowest_wait() -> None:
    assert recommended_ids(snapshot_with_waits(3.0, 1.0, 2.0)) == [2]


def test_tie_recommends_smallest_register_id() -> None:
    assert recommended_ids(snapshot_with_waits(2.0, 0.0, 0.0)) == [2]


def test_queue_length_is_copied_from_snapshot() -> None:
    register = RegisterSnapshot(
        1, serving_customer_id=7, waiting_customer_ids=(8, 9), estimated_wait=4.0
    )
    snapshot = StoreSnapshot(0.0, (register,), 0, 0)
    assert build_board(snapshot)[0].queue_length == 3


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0.0, "0 min"), (0.75, "45 s"), (2.5, "2 min 30 s"), (3.0, "3 min"),
     (1.999, "2 min"), (12.25, "12 min 15 s")],
)
def test_format_minutes(minutes: float, expected: str) -> None:
    assert format_minutes(minutes) == expected


def test_format_minutes_rejects_negative() -> None:
    with pytest.raises(ValueError):
        format_minutes(-1.0)
