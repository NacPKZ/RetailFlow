"""V7 : appariement, coûts, choix conditionnel et conservation FIFO."""

import io
import json
import shutil
import subprocess
import zipfile
from dataclasses import replace

import pandas as pd
import pytest

from queuesmart.analytics.decision_lab import (
    DecisionAssumptions,
    compare_dynamic_capacity,
    decision_bundle,
    decision_report,
    recommend_capacity,
)
from queuesmart.analytics.dynamic_metrics import final_metrics, resource_frame
from queuesmart.config import ScenarioConfig
from queuesmart.scene.layout import SceneLayout
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine

CONFIG = ScenarioConfig("Décision V7", 45, 20, 1.8, 2, 42)
OPTIONS = DynamicOptions(patience_min=4, switching_enabled=True)


def test_costs_and_service_denominators_match_actual_dynamic_run():
    assumptions = DecisionAssumptions(24, 7, 2, 90)
    summary, trials = compare_dynamic_capacity(CONFIG, OPTIONS, assumptions, 3, 2)
    assert len(trials) == 6
    assert all(trials.groupby("Caisses")["Graine"].apply(list).map(tuple) == (42, 43))
    for row in trials.to_dict("records"):
        result = DynamicSimulationEngine().run(
            CONFIG.with_registers(row["Caisses"]).with_seed(row["Graine"]), OPTIONS
        )
        minutes = resource_frame(result)["Mobilisation (min)"].sum()
        expected = minutes / 60 * 24 + result.abandoned_count * 7
        assert row["Coût modélisé (€)"] == pytest.approx(expected)
        assert row["Service (%)"] == pytest.approx(
            100
            * sum(c.service_start is not None and c.wait_time <= 2 for c in result.customers)
            / CONFIG.customer_count
        )
        assert row["Servis"] + row["Abandons"] == CONFIG.customer_count
    assert summary["Service minimum (%)"].tolist() == (
        trials.groupby("Caisses")["Service (%)"].min().tolist()
    )
    report = decision_report(CONFIG, OPTIONS, assumptions, summary, trials)
    assert "hypothétique" in report and report.startswith("# RetailFlow V7.0")
    assert "intervalle" in report and "tous les arrivants" in report


def test_capacity_pairing_uses_identical_customers(monkeypatch):
    actual = DynamicSimulationEngine.run
    populations = {}

    def record(self, config, options):
        result = actual(self, config, options)
        population = [(c.customer_id, c.arrival_time, c.service_duration) for c in result.customers]
        if config.seed in populations:
            assert populations[config.seed] == population
        populations[config.seed] = population
        return result

    monkeypatch.setattr(DynamicSimulationEngine, "run", record)
    compare_dynamic_capacity(CONFIG, OPTIONS, DecisionAssumptions(), 5, 2)
    assert len(populations) == 2


def test_recommendation_filters_feasibility_before_cost_and_uses_unrounded_values():
    frame = pd.DataFrame(
        [
            {"Caisses": 1, "Admissible": False, "Coût modélisé (€)": 1},
            {"Caisses": 2, "Admissible": True, "Coût modélisé (€)": 30.004},
            {"Caisses": 3, "Admissible": True, "Coût modélisé (€)": 30.003},
        ]
    )
    assert recommend_capacity(frame) == 3
    frame["Admissible"] = False
    assert recommend_capacity(frame) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"hourly_cost": -1},
        {"abandonment_cost": float("nan")},
        {"wait_target": 0},
        {"service_target": 101},
        {"hourly_cost": float("inf")},
    ],
)
def test_invalid_assumptions_rejected(changes):
    with pytest.raises(ValueError):
        DecisionAssumptions(**changes)


def test_unsupported_comparisons_rejected():
    for maximum, runs in [(6, 2), (2, 0), (True, 2), (2, 21)]:
        with pytest.raises(ValueError):
            compare_dynamic_capacity(CONFIG, OPTIONS, DecisionAssumptions(), maximum, runs)
    with pytest.raises(ValueError):
        compare_dynamic_capacity(CONFIG.with_seed(None), OPTIONS, DecisionAssumptions())
    with pytest.raises(ValueError):
        compare_dynamic_capacity(
            CONFIG, replace(OPTIONS, register_changes=((1, 3, True),)), DecisionAssumptions()
        )


def test_compact_geometry_is_exactly_one_line_with_six_visible_slots():
    layout = SceneLayout(compact=True)
    assert layout.to_dict()["visible_queue_limit"] == 6
    for rid in range(1, 6):
        spots = [layout.queue_slot(rid, rank) for rank in range(1, 501)]
        assert len(set(spots)) == 500
        assert all(p.x == layout.lane_x(rid) for p in spots)
        assert all(6 < p.y < 11 for p in spots)
        assert all(a.y < b.y for a, b in zip(spots, spots[1:], strict=False))


@pytest.mark.parametrize("switching", [False, True])
def test_fifo_and_uniqueness_for_each_event_with_transfers_and_abandons(switching):
    result = DynamicSimulationEngine().run(
        CONFIG,
        replace(
            OPTIONS, switching_enabled=switching, register_changes=((5, 3, True), (10, 1, False))
        ),
    )
    queues = {r: [] for r in range(1, 6)}
    for e in result.events:
        if e.type == "queue_joined":
            queues[e.register_id].append(e.customer_id)
        elif e.type == "service_started":
            assert queues[e.register_id].pop(0) == e.customer_id
        elif e.type in ("queue_switched", "customer_abandoned"):
            queues[e.register_id].remove(e.customer_id)
            if e.target_register_id is not None:
                queues[e.target_register_id].append(e.customer_id)
        ids = [cid for q in queues.values() for cid in q]
        assert len(ids) == len(set(ids))
    assert not any(queues.values())


def test_javascript_operations_match_python_final_metrics_and_prefix():
    if not shutil.which("node"):
        pytest.skip("Node requis")
    result = DynamicSimulationEngine().run(CONFIG, OPTIONS)
    script = """
const fs=require('fs'),vm=require('vm');const env={RF:{}};vm.createContext(env);
vm.runInContext(fs.readFileSync('frontend_studio/operations.js','utf8'),env);
const data=JSON.parse(fs.readFileSync(0,'utf8')),o=new env.RF.Operations(data);
process.stdout.write(JSON.stringify(o.at(1000)));
"""
    output = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        input=json.dumps({"initially_open": 2, "events": result.events_as_dicts()}),
    )
    js = json.loads(output.stdout)
    metrics = final_metrics(result)
    assert js["occupation"] == pytest.approx(metrics["Occupation des ressources (%)"])
    assert js["meanWait"] == pytest.approx(metrics["Attente moyenne des servis (min)"])
    assert js["p90"] == pytest.approx(metrics["P90 des servis (min)"])
    assert js["served"] == result.served_count


def test_studio_mount_lifecycle_with_actual_payload():
    if not shutil.which("node"):
        pytest.skip("Node requis")
    from queuesmart.ui.studio_component import studio_payload

    result = DynamicSimulationEngine().run(
        replace(CONFIG, customer_count=100, open_registers=1),
        replace(OPTIONS, patience_min=30, switching_enabled=False),
    )
    output = subprocess.run(
        ["node", "tests/studio_mount.cjs"],
        input=json.dumps(studio_payload(result, "mount-v7", 0, {})),
        text=True,
        capture_output=True,
    )
    assert output.returncode == 0, output.stdout + output.stderr


def test_export_bundle_contains_reproducible_parameters_and_excel_csv():
    assumptions = DecisionAssumptions()
    summary, trials = compare_dynamic_capacity(CONFIG, OPTIONS, assumptions, 2, 2)
    output = decision_bundle(
        CONFIG, OPTIONS, assumptions, summary, trials, "<html>graphique</html>"
    )
    with zipfile.ZipFile(io.BytesIO(output)) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            "rapport.md",
            "capacites.csv",
            "tirages.csv",
            "hypotheses.json",
            "frontiere.html",
        }
        assert archive.read("capacites.csv").startswith(b"\xef\xbb\xbf")
        assert len(pd.read_csv(io.BytesIO(archive.read("tirages.csv")), sep=";", decimal=",")) == 4
        metadata = json.loads(archive.read("hypotheses.json"))
        assert metadata["runs"] == 2 and metadata["config"]["seed"] == 42
        assert archive.read("frontiere.html") == b"<html>graphique</html>"


def test_dense_scene_retains_all_customers_with_bounded_visual_payload():
    from queuesmart.scene.html import scene_data

    config = ScenarioConfig("Charge V7", 500, 60, 1.7, 2, 42)
    result = DynamicSimulationEngine().run(config, DynamicOptions())
    payload = scene_data(result, SceneLayout(compact=True))
    assert {c["id"] for c in payload["customers"]} == set(range(1, 501))
    assert payload["events"] == result.events_as_dicts()
    assert len(json.dumps(payload).encode()) < 750_000


def test_final_export_includes_quantiles_and_abandonment_denominator():
    result = DynamicSimulationEngine().run(CONFIG, OPTIONS)
    metrics = final_metrics(result)
    waits = pd.Series([c.wait_time for c in result.customers if c.service_start is not None])
    assert metrics["Médiane des servis (min)"] == pytest.approx(waits.median())
    assert metrics["P95 des servis (min)"] == pytest.approx(waits.quantile(0.95))
    assert metrics["Taux d'abandon (%)"] == pytest.approx(
        100 * result.abandoned_count / len(result.customers)
    )
