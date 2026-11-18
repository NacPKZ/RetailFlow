"""Actions réelles, conservation des clients et stabilité du passé."""

from dataclasses import replace

import pytest

from queuesmart.analytics.interventions import (
    apply_interventions,
    state_at,
    validate_intervention,
)
from queuesmart.analytics.narrative import compare_results, describe_result
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine

CONFIG = ScenarioConfig("Interventions", 80, 12.0, 3.0, 2, seed=42)
ENGINE = DynamicSimulationEngine()
BASE = DynamicOptions(patience_min=None, switching_enabled=False)


def waiting_context():
    result = ENGINE.run(CONFIG, BASE)
    for event in result.events:
        time = event.time + 0.000001
        state = state_at(result, time)
        source = next((r for r, q in state["queues"].items() if q), None)
        if source:
            target = 1 if source == 2 else 2
            return result, time, state["queues"][source][0], source, target
    raise AssertionError("Le scénario doit former une file.")


def test_manual_move_is_applied_and_keeps_customer_generation_and_past():
    original, time, cid, source, target = waiting_context()
    command = validate_intervention(
        original, {"kind": "move", "time": time, "customer_id": cid, "register_id": target}
    )
    changed = ENGINE.run(CONFIG, apply_interventions(BASE, [command]))
    move = next(e for e in changed.events if e.type == "queue_switched" and e.time == time)
    assert (move.customer_id, move.register_id, move.target_register_id) == (cid, source, target)
    assert [e for e in original.events if e.time < time] == [
        e for e in changed.events if e.time < time
    ]
    assert [(c.arrival_time, c.service_duration) for c in changed.customers] == [
        (c.arrival_time, c.service_duration) for c in original.customers
    ]
    assert changed.served_count + changed.abandoned_count == CONFIG.customer_count
    assert state_at(changed, time)["queues"][source].count(cid) == 0


def test_manual_assignment_is_not_undone_by_auto_switching():
    original, time, cid, _, target = waiting_context()
    options = replace(
        BASE, switching_enabled=True, switching_gain_min=0, customer_moves=((time, cid, target),)
    )
    changed = ENGINE.run(CONFIG, options)
    later_moves = [
        e
        for e in changed.events
        if e.type == "queue_switched" and e.customer_id == cid and e.time > time
    ]
    assert not later_moves


def test_register_click_closes_and_reassigns_without_interrupting_service():
    original, time, _, source, _ = waiting_context()
    serving_id = state_at(original, time)["serving"][source]
    command = validate_intervention(
        original, {"kind": "register", "time": time, "register_id": source, "opened": False}
    )
    changed = ENGINE.run(CONFIG, apply_interventions(BASE, [command]))
    assert any(e.type == "register_closed" and e.time == time for e in changed.events)
    person = next(c for c in original.customers if c.customer_id == serving_id)
    after = next(c for c in changed.customers if c.customer_id == serving_id)
    assert after.departure_time == person.departure_time
    assert not state_at(changed, time)["queues"][source]


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "register", "time": float("nan"), "register_id": 1, "opened": False},
        {"kind": "register", "time": -1, "register_id": 1, "opened": False},
        {"kind": "register", "time": 1, "register_id": True, "opened": False},
        {"kind": "move", "time": 1, "register_id": 3, "customer_id": 1},
        {"kind": "unknown", "time": 1, "register_id": 1},
        {"kind": "register", "time": 1, "register_id": 8, "opened": True},
    ],
)
def test_invalid_commands_are_rejected(payload):
    with pytest.raises(ValueError):
        validate_intervention(ENGINE.run(CONFIG, BASE), payload)


def test_last_open_register_cannot_be_closed():
    result = ENGINE.run(CONFIG.with_registers(1), BASE)
    with pytest.raises(ValueError, match="dernière"):
        validate_intervention(
            result, {"kind": "register", "time": 1, "register_id": 1, "opened": False}
        )


def test_serving_customer_cannot_be_dragged():
    result, time, _, _, target = waiting_context()
    cid = next(c for c in state_at(result, time)["serving"].values() if c is not None)
    with pytest.raises(ValueError, match="encore dans une file"):
        validate_intervention(
            result, {"kind": "move", "time": time, "customer_id": cid, "register_id": target}
        )


def test_patience_does_not_restart_after_a_move():
    config = replace(CONFIG, customer_count=150, open_registers=2)
    options = replace(BASE, patience_min=1.0)
    original = ENGINE.run(config, options)
    event = next(e for e in original.events if e.type == "customer_abandoned")
    cid, deadline = event.customer_id, event.time
    time = deadline - 0.1
    state = state_at(original, time)
    source = next(r for r, q in state["queues"].items() if cid in q)
    target = 1 if source == 2 else 2
    changed = ENGINE.run(config, replace(options, customer_moves=((time, cid, target),)))
    person = next(c for c in changed.customers if c.customer_id == cid)
    assert person.abandoned_at is None or person.abandoned_at == pytest.approx(deadline)


def test_analysis_and_reference_delta_are_explicit():
    result = ENGINE.run(CONFIG, BASE)
    sentences = describe_result(result)
    assert len(sentences) == 4
    assert str(CONFIG.customer_count) in sentences[0][1]
    assert all(value == 0 for value in compare_results(result, result).values())


def test_gestures_at_same_instant_keep_user_order():
    original, time, cid, source, target = waiting_context()
    move = validate_intervention(
        original, {"kind": "move", "time": time, "customer_id": cid, "register_id": target}
    )
    moved = ENGINE.run(CONFIG, apply_interventions(BASE, [move]))
    close = validate_intervention(
        moved, {"kind": "register", "time": time, "register_id": target, "opened": False}
    )
    changed = ENGINE.run(CONFIG, apply_interventions(BASE, [move, close]))
    at_time = [e for e in changed.events if e.time == time]
    manual_move = next(
        i
        for i, e in enumerate(at_time)
        if e.type == "queue_switched" and e.customer_id == cid and e.target_register_id == target
    )
    closing = next(i for i, e in enumerate(at_time) if e.type == "register_closed")
    assert manual_move < closing
    assert changed.served_count == CONFIG.customer_count
