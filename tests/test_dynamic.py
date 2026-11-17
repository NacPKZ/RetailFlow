from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine


def config(n=30, registers=3):
    return ScenarioConfig('Test', n, 30.0, 2.0, registers, seed=42)


def test_all_customers_accounted_for():
    result = DynamicSimulationEngine().run(config())
    assert result.served_count + result.abandoned_count == 30
    assert len(result.customers) == 30
    assert all(c.wait_time is not None for c in result.customers)


def test_deterministic():
    engine = DynamicSimulationEngine()
    assert engine.run(config()).events == engine.run(config()).events


def test_patience_abandonments():
    result = DynamicSimulationEngine().run(config(100, 1), DynamicOptions(patience_min=0.01))
    assert result.abandoned_count > 0
    assert any(e.type == 'customer_abandoned' for e in result.events)


def test_open_register():
    result = DynamicSimulationEngine().run(config(50, 1), DynamicOptions(register_changes=((5.0, 2, True),)))
    assert any(e.type == 'register_opened' and e.register_id == 2 for e in result.events)
    assert any(c.register_id == 2 for c in result.customers)


def test_close_register_reassign():
    result = DynamicSimulationEngine().run(config(100, 2), DynamicOptions(register_changes=((3.0, 2, False),)))
    assert any(e.type == 'register_closed' for e in result.events)
    assert any(e.type == 'queue_switched' for e in result.events)
    assert result.served_count + result.abandoned_count == 100


def test_switching_event():
    result = DynamicSimulationEngine().run(config(100, 3), DynamicOptions(patience_min=None, switching_gain_min=0.0))
    assert result.served_count == 100
    assert all(e.type != 'customer_abandoned' for e in result.events)


def test_no_close_last_register():
    result = DynamicSimulationEngine().run(config(30, 1), DynamicOptions(register_changes=((1.0, 1, False),)))
    assert result.served_count + result.abandoned_count == 30
    assert not any(e.type == 'register_closed' for e in result.events)


def test_event_times_non_decreasing():
    result = DynamicSimulationEngine().run(config(100, 3))
    assert all(a.time <= b.time for a, b in zip(result.events, result.events[1:]))
