"""Contrats du dashboard et contrôles croisés entre journal, KPI et exports."""

import json
from dataclasses import replace
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from queuesmart.analytics.decision_lab import mean_wait_capacity
from queuesmart.analytics.dynamic_alerts import saturation_periods
from queuesmart.analytics.dynamic_kpi import queue_frame, register_performance
from queuesmart.analytics.dynamic_metrics import final_metrics
from queuesmart.analytics.visual_data import customer_frame
from queuesmart.config import ScenarioConfig
from queuesmart.exports.dynamic import csv_bytes, excel_bytes, experiment_payload
from queuesmart.simulation.dynamic import (
    DynamicCustomerResult,
    DynamicEvent,
    DynamicOptions,
    DynamicResult,
    DynamicSimulationEngine,
)


@pytest.mark.parametrize("registers", range(1, 6))
def test_replay_preserves_clients_and_matches_register_totals(registers):
    config = ScenarioConfig("Test", 110, 60.0, 1.7, registers, 42)
    options = DynamicOptions(patience_min=2, register_changes=((5.0, 5, True), (12.0, 5, False)))
    result = DynamicSimulationEngine().run(config, options)
    queues = queue_frame(result)
    totals = queues.groupby("Minute").agg(
        arrivals=("Arrivés", "first"),
        served=("Servis", "first"),
        abandoned=("Abandons", "first"),
        queued=("En file", "sum"),
        serving=("En service", "sum"),
    )
    assert (
        totals.arrivals == totals.served + totals.abandoned + totals.queued + totals.serving
    ).all()
    assert totals.iloc[-1].arrivals == 110
    assert totals.iloc[-1].served == result.served_count
    report = register_performance(result, queues)
    assert report["Servis"].sum() == result.served_count
    assert report["Service (min)"].sum() == pytest.approx(
        sum(c.service_duration for c in result.customers if c.departure_time is not None)
    )
    assert report["Occupation (%)"].dropna().between(0, 100).all()


def test_empty_partial_and_abandoned_have_distinct_populations():
    config = ScenarioConfig("Test", 1, 5, 5, 1, 42)
    result = DynamicResult(config, DynamicOptions(), (), ())
    assert final_metrics(result)["Clients arrivés"] == 0
    assert len(queue_frame(result)) == 5
    arrived = DynamicEvent(1, "customer_arrived", 1)
    joined = DynamicEvent(1, "queue_joined", 1, 1)
    customer = DynamicCustomerResult(1, 1, 5, 1, None, None, None)
    partial = replace(result, events=(arrived, joined), customers=(customer,))
    assert final_metrics(partial)["Clients encore présents"] == 1
    assert final_metrics(partial)["Attente moyenne des servis (min)"] is None
    assert queue_frame(partial).iloc[-5:]["En file"].sum() == 1
    abandoned = replace(
        partial,
        events=(*partial.events, DynamicEvent(3, "customer_abandoned", 1, 1)),
        customers=(replace(customer, abandoned_at=3),),
    )
    kpis = final_metrics(abandoned)
    assert kpis["Temps moyen avant abandon (min)"] == 2
    assert kpis["Taux d'abandon (%)"] == 100
    assert saturation_periods(queue_frame(abandoned), 1) == [
        {"Caisse": 1, "Début (min)": 1, "Fin (min)": 3, "Pic de file": 1}
    ]


def test_exports_use_the_same_values_and_can_be_read():
    config = ScenarioConfig("Test", 24, 15.0, 1.7, 2, 42)
    result = DynamicSimulationEngine().run(config, DynamicOptions())
    metrics = final_metrics(result)
    kpis = pd.DataFrame(metrics.items(), columns=["Indicateur", "Valeur"])
    payload = experiment_payload(result, metrics, [])
    tables = {"Résumé KPI": kpis, "Clients": customer_frame(result), "Files": queue_frame(result)}
    workbook = load_workbook(BytesIO(excel_bytes(tables, payload)), read_only=True)
    assert workbook.sheetnames == ["Paramètres", "Résumé KPI", "Clients", "Files"]
    assert workbook["Clients"].max_row == 25
    for key, value in list(workbook["Résumé KPI"].values)[1:]:
        if value is not None:
            assert value == pytest.approx(metrics[key])
    csv = pd.read_csv(BytesIO(csv_bytes(kpis)), sep=";", decimal=",")
    assert csv.iloc[0].Valeur == 24
    assert json.loads(json.dumps(payload, allow_nan=False))["configuration"]["seed"] == 42


def test_mean_wait_selects_minimum_capacity_with_all_seeds_compliant():
    trials = pd.DataFrame(
        {
            "Caisses": [1, 1, 2, 2, 3, 3],
            "Graine": [42, 43] * 3,
            "Attente moyenne (min)": [None, 0, 1, 6, 2, 4],
            "Taux d'abandon (%)": [100, 70, 5, 0, 2, 6],
        }
    )
    frame, selected = mean_wait_capacity(trials, 5.0)
    assert selected == 3
    assert frame["Tirages conformes"].tolist() == [1, 1, 2]
    assert frame.iloc[2]["Taux d’abandon moyen (%)"] == 4


def test_wait_quantiles_and_busy_time_with_simultaneous_events():
    config = ScenarioConfig("Test", 2, 5.0, 2.0, 1, 42)
    result = DynamicResult(
        config,
        DynamicOptions(),
        (
            DynamicEvent(0, "customer_arrived", 1),
            DynamicEvent(0, "queue_joined", 1, 1),
            DynamicEvent(0, "service_started", 1, 1),
            DynamicEvent(0, "customer_arrived", 2),
            DynamicEvent(0, "queue_joined", 2, 1),
            DynamicEvent(4, "customer_departed", 1, 1),
            DynamicEvent(4, "service_started", 2, 1),
            DynamicEvent(6, "customer_departed", 2, 1),
            DynamicEvent(9, "register_opened", register_id=2),
        ),
        (
            DynamicCustomerResult(1, 0, 4, 1, 0, 4, None),
            DynamicCustomerResult(2, 0, 2, 1, 4, 6, None),
        ),
    )
    metrics = final_metrics(result)
    assert metrics["Fin d’observation (min)"] == 6
    assert metrics["Attente moyenne des servis (min)"] == 2
    assert metrics["Médiane des servis (min)"] == 2
    assert metrics["P90 des servis (min)"] == pytest.approx(3.6)
    assert metrics["P95 des servis (min)"] == pytest.approx(3.8)
    assert metrics["Service moyen des servis (min)"] == 3
    assert metrics["Temps dans le système des servis (min)"] == 5
    assert metrics["Débit (servis/min)"] == pytest.approx(1 / 3)
    assert metrics["Occupation des ressources (%)"] == 100
    queues = queue_frame(result)
    assert queues["Minute"].unique().tolist() == [0, 4, 6]
    assert queues.query("Caisse == 1")["En file"].tolist() == [1, 0, 0]
