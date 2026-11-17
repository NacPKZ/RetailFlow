from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.events import events_from_result
from queuesmart.simulation.strategies import build_strategy


def test_event_stream_complete_and_deterministic():
    engine = SimulationEngine(build_strategy("shortest_queue"))
    config = ScenarioConfig("demo", 30, 30.0, 2.0, 3, seed=42)
    first = events_from_result(engine.run(config))
    second = events_from_result(engine.run(config))
    assert first == second
    assert len(first) == 120
    assert [e.time for e in first] == sorted(e.time for e in first)
    for kind in ("customer_arrived", "queue_joined", "service_started", "customer_departed"):
        assert sum(e.type == kind for e in first) == 30
    assert all(e.queue_position is not None and e.queue_position >= 1 for e in first if e.type == "queue_joined")
