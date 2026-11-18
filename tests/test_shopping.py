"""Parcours de courses illustratifs, distincts de la mesure des caisses."""

from queuesmart.config import ScenarioConfig
from queuesmart.scene.layout import MAIN_AISLE_Y, STORE_HEIGHT
from queuesmart.scene.shopping import shopping_tracks
from queuesmart.simulation.dynamic import DynamicSimulationEngine


def test_shopping_is_deterministic_and_ends_at_checkout_arrival():
    result = DynamicSimulationEngine().run(ScenarioConfig("Courses", 50, 60.0, 1.6, 3, seed=42))
    first = shopping_tracks(result)
    assert first == shopping_tracks(result)
    assert len(first) == len(result.customers)
    for track, person in zip(first, result.customers, strict=True):
        assert track["end"] == person.arrival_time
        assert 4 - 1e-8 <= track["end"] - track["start"] <= 10.0000001
        assert track["keyframes"][-1][3] == "parti"
        assert track["keyframes"][-1][2] == MAIN_AISLE_Y
        assert all(
            0 <= frame[1] <= 24 and 0 <= frame[2] <= STORE_HEIGHT for frame in track["keyframes"]
        )
        assert all(
            a[0] < b[0] for a, b in zip(track["keyframes"], track["keyframes"][1:], strict=False)
        )


def test_initial_shoppers_are_possible_but_not_all_customers():
    result = DynamicSimulationEngine().run(ScenarioConfig("Courses", 50, 60.0, 1.6, 3, seed=42))
    tracks = shopping_tracks(result)
    initial = [p for p in tracks if p["start"] <= 0 < p["end"]]
    assert 0 < len(initial) < len(tracks)
