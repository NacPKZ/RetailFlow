"""Calculs à la main et invariants sur les données affichées."""

import numpy as np
import pandas as pd
import pytest

from queuesmart.analytics.visual_data import (
    compare_capacity,
    customer_frame,
    flow_frame,
    register_frame,
    service_level,
)
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.strategies import build_strategy
from queuesmart.ui import charts


def test_simultaneous_events_and_abandonment_balance():
    clients = pd.DataFrame(
        [
            {"Arrivée": 0.0, "Début": 0.0, "Sortie": 2.0, "Abandon": None, "Statut": "Servi"},
            {"Arrivée": 1.0, "Début": 2.0, "Sortie": 3.0, "Abandon": None, "Statut": "Servi"},
            {"Arrivée": 1.0, "Début": None, "Sortie": None, "Abandon": 2.0, "Statut": "Abandon"},
        ]
    )
    flow = flow_frame(clients).set_index("Minute")
    assert flow.loc[1.0, ["En attente", "En service", "Servis", "Abandons"]].tolist() == [
        2,
        1,
        0,
        0,
    ]
    assert flow.loc[2.0, ["En attente", "En service", "Servis", "Abandons"]].tolist() == [
        0,
        1,
        1,
        1,
    ]
    assert flow.loc[3.0, ["En attente", "En service", "Servis", "Abandons"]].tolist() == [
        0,
        0,
        2,
        1,
    ]


def test_service_level_counts_abandonment_as_failure_even_if_wait_is_short():
    clients = pd.DataFrame({"Statut": ["Servi", "Servi", "Abandon"], "Attente": [0.0, 5.0, 1.0]})
    assert service_level(clients) == pytest.approx(200 / 3)


@pytest.mark.parametrize("dynamic", [False, True])
def test_conservation_for_generated_customers(dynamic):
    config = ScenarioConfig("Congestion", 100, 5.0, 3.0, 2, seed=2)
    result = (
        DynamicSimulationEngine().run(config, DynamicOptions(patience_min=1))
        if dynamic
        else SimulationEngine(build_strategy("shortest_queue")).run(config)
    )
    clients = customer_frame(result)
    flow = flow_frame(clients)
    assert (flow.iloc[:, 1:] >= 0).all().all()
    assert flow.iloc[-1]["En attente"] == flow.iloc[-1]["En service"] == 0
    assert flow.iloc[-1]["Servis"] + flow.iloc[-1]["Abandons"] == config.customer_count
    for row in flow.to_dict("records"):
        arrived = (clients["Arrivée"] <= row["Minute"]).sum()
        assert sum(row[c] for c in ["En attente", "En service", "Servis", "Abandons"]) == arrived


def test_unused_registers_and_service_time_are_preserved():
    clients = pd.DataFrame(
        {
            "Caisse": [1, 1],
            "Service": [2.0, 3.0],
            "Attente": [0.0, 1.0],
            "Statut": ["Servi", "Servi"],
        }
    )
    frame = register_frame(clients, 2, 10.0)
    assert frame["Occupation (%)"].tolist() == [50.0, 0.0]
    assert frame["Clients"].tolist() == [2, 0]


def test_histogram_keeps_zeroes_and_exact_threshold_in_correct_group():
    clients = pd.DataFrame({"Attente": [0.0, 0.0, 5.0, 5.01, 10.0]})
    figure = charts.wait_histogram(clients)
    assert sum(figure.data[0].y) == 3
    assert sum(figure.data[1].y) == 2
    ecdf = charts.wait_ecdf(clients)
    assert list(ecdf.data[0].x) == [0.0, 5.0, 5.01, 10.0]
    assert list(ecdf.data[0].y) == [40.0, 60.0, 80.0, 100.0]


def test_capacity_uses_reproducible_replications_and_two_service_targets():
    config = ScenarioConfig("Capacité", 20, 10.0, 2.0, 1, seed=42)
    first = compare_capacity(config, "least_wait", 3, 3)
    second = compare_capacity(config, "least_wait", 3, 3)
    pd.testing.assert_frame_equal(first, second)
    expected = (first["P90"] <= 5) & (first["Sous 5 min (%)"] >= 90)
    assert first["Objectif atteint"].tolist() == expected.tolist()
    assert (first["Minimum des moyennes"] <= first["Attente moyenne"] + 1e-9).all()
    assert (first["Maximum des moyennes"] >= first["Attente moyenne"] - 1e-9).all()


def test_heatmap_marks_absent_groups_as_missing_not_zero():
    clients = pd.DataFrame({"Caisse": [1, 1], "Arrivée": [1.0, 25.0], "Attente": [0.0, 8.0]})
    heatmap = charts.wait_heatmap(clients, 2)
    assert heatmap.data[0].z[0, 0] == 0
    assert np.isnan(heatmap.data[0].z[0, 1])
    assert np.isnan(heatmap.data[0].z[1, :]).all()
