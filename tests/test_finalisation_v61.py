"""Régressions temporelles, comparaison appariée et contrat scène/Python."""

import json
import shutil
import subprocess
from dataclasses import asdict, replace

import pytest

from queuesmart.analytics.dynamic_metrics import final_metrics, paired_metrics, resource_frame
from queuesmart.analytics.interventions import Intervention, apply_interventions, state_at
from queuesmart.analytics.visual_data import customer_frame, service_level
from queuesmart.config import ScenarioConfig
from queuesmart.scene.layout import SceneLayout
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine
from queuesmart.ui import charts
from queuesmart.ui.studio_component import studio_payload

CONFIG = ScenarioConfig("Validation V6.1", 60, 15.0, 2.0, 2, seed=42)
ENGINE = DynamicSimulationEngine()
BASE = DynamicOptions(patience_min=4.0)


def test_manual_command_follows_observed_patience_at_the_same_instant():
    original = ENGINE.run(CONFIG, BASE)
    deadline = next(e.time for e in original.events if e.type == "customer_abandoned")
    changed = ENGINE.run(
        CONFIG, apply_interventions(BASE, [Intervention(deadline, "register", 3, opened=True)])
    )
    prefix = [e for e in changed.events if e.time <= deadline]
    assert prefix[: len([e for e in original.events if e.time <= deadline])] == [
        e for e in original.events if e.time <= deadline
    ]
    assert changed.action_outcomes[0].applied


def test_earlier_edit_marks_later_command_as_inapplicable_and_undo_is_exact():
    actions = [
        Intervention(10, "register", 3, opened=True),
        Intervention(1, "register", 3, opened=True),
    ]
    changed = ENGINE.run(CONFIG, apply_interventions(BASE, actions))
    outcomes = {o.index: o for o in changed.action_outcomes}
    assert outcomes[1].applied and not outcomes[0].applied
    assert "déjà" in outcomes[0].reason
    assert outcomes[1].before != outcomes[1].after
    actions.pop()
    assert ENGINE.run(CONFIG, apply_interventions(BASE, actions)) == ENGINE.run(
        CONFIG, apply_interventions(BASE, actions[:1])
    )
    actions.pop()
    assert ENGINE.run(CONFIG, apply_interventions(BASE, actions)) == ENGINE.run(CONFIG, BASE)


@pytest.mark.parametrize("count", [10, 60, 100, 110])
@pytest.mark.parametrize("registers", [1, 2, 3, 4, 5])
def test_conservation_at_event_times_and_reproducibility(count, registers):
    config = replace(CONFIG, customer_count=count, open_registers=registers)
    result = ENGINE.run(config, BASE)
    assert result == ENGINE.run(config, BASE)
    for time in sorted({e.time for e in result.events})[::5]:
        state = state_at(result, time)
        arrived = sum(c.arrival_time <= time for c in result.customers)
        exited = sum(
            c.departure_time is not None and c.departure_time <= time for c in result.customers
        )
        abandoned = sum(
            c.abandoned_at is not None and c.abandoned_at <= time for c in result.customers
        )
        waiting = sum(map(len, state["queues"].values()))
        in_service = sum(c is not None for c in state["serving"].values())
        assert arrived == waiting + in_service + exited + abandoned
        assert all(not q or state["opened"][r] for r, q in state["queues"].items())
    assert result.served_count + result.abandoned_count == count


def test_occupation_accounts_for_closed_register_finishing_service():
    original = ENGINE.run(CONFIG, BASE)
    start = next(e for e in original.events if e.type == "service_started")
    time = start.time + 0.000001
    changed = ENGINE.run(
        CONFIG,
        apply_interventions(
            BASE, [Intervention(time, "register", start.register_id, opened=False)]
        ),
    )
    resources = resource_frame(changed)
    person = next(c for c in changed.customers if c.customer_id == start.customer_id)
    assert resources.iloc[start.register_id - 1]["Mobilisation (min)"] == pytest.approx(
        person.departure_time
    )
    assert resources["Service (min)"].sum() == pytest.approx(
        sum(c.service_duration for c in changed.customers if c.service_start is not None)
    )
    assert all(row["Écart"] == 0 for row in paired_metrics(changed, changed))
    assert 0 <= final_metrics(changed)["Occupation des ressources (%)"] <= 100


def test_all_empty_charts_are_serializable_and_service_level_is_defined():
    empty = customer_frame(ENGINE.run(CONFIG, BASE)).iloc[:0]
    assert service_level(empty) == 0
    figures = [
        charts.wait_scatter(empty),
        charts.wait_histogram(empty),
        charts.wait_ecdf(empty),
        charts.wait_heatmap(empty, 5),
        charts.congestion(empty),
        charts.arrival_chart(empty),
        charts.cumulative_flow(empty),
        charts.service_timeline(empty),
    ]
    for figure in figures:
        assert json.loads(figure.to_json())["layout"]["title"]["text"]


def test_long_queue_virtual_coordinates_stay_in_their_lane():
    layout = SceneLayout(compact=True)
    for register in range(1, 6):
        slots = [layout.queue_slot(register, rank) for rank in range(1, 111)]
        assert len(set(slots)) == 110
        assert all(
            layout.lane_x(register) <= p.x <= layout.lane_x(register) + 1.8 and 6 <= p.y < 11
            for p in slots
        )


def test_actual_payload_replay_matches_python_even_when_seeking_backwards():
    if not shutil.which("node"):
        pytest.skip("Node requis pour vérifier le contrat navigateur/Python")
    result = ENGINE.run(CONFIG, BASE)
    payload = studio_payload(result, "test", 0, {})
    times = [0, *sorted({e.time for e in result.events})[::7]]
    times += list(reversed(times))
    script = """
const fs=require('node:fs'),vm=require('node:vm');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const env={RF:{}};vm.createContext(env);
vm.runInContext(fs.readFileSync('frontend_studio/replay.js','utf8'),env);
const r=new env.RF.Replay(x.data);process.stdout.write(JSON.stringify(x.times.map(t=>r.at(t))));
"""
    output = subprocess.run(
        ["node", "-e", script],
        input=json.dumps({"data": payload, "times": times}),
        text=True,
        capture_output=True,
        check=True,
    )
    for time, actual in zip(times, json.loads(output.stdout), strict=True):
        state = state_at(result, time)
        assert actual["queues"] == {str(k): v for k, v in state["queues"].items()}
        assert actual["open"] == {str(k): v for k, v in state["opened"].items()}
        assert actual["serving"] == {str(k): v for k, v in state["serving"].items()}
        assert actual["arrivals"] == sum(c.arrival_time <= time for c in result.customers)
    # Le bilan exportable est JSON strict, sans NaN ni valeur finale dans le lecteur.
    json.dumps(
        {"metrics": final_metrics(result), "outcomes": [asdict(o) for o in result.action_outcomes]},
        allow_nan=False,
    )


@pytest.mark.parametrize("field", ["patience_min", "switching_interval_min", "switching_gain_min"])
@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_nonfinite_options_are_rejected_instead_of_blocking_replay(field, value):
    with pytest.raises(ValueError):
        DynamicOptions(**{field: value})


def test_one_hundred_commands_and_successive_undos_are_reproducible():
    actions = [Intervention(1 + i / 100, "register", 3, opened=i % 2 == 0) for i in range(100)]
    for retained in [100, 50, 10, 1, 0]:
        options = apply_interventions(BASE, actions[:retained])
        result = ENGINE.run(CONFIG, options)
        assert result == ENGINE.run(CONFIG, options)
        assert len(result.action_outcomes) == retained
        assert all(o.applied for o in result.action_outcomes)
        assert result.served_count + result.abandoned_count == CONFIG.customer_count
    assert ENGINE.run(CONFIG, apply_interventions(BASE, [])) == ENGINE.run(CONFIG, BASE)


def test_defense_backup_is_reproducible_and_does_not_claim_service_target(tmp_path):
    from scripts.prepare_soutenance import prepare

    first = prepare(tmp_path / "first.json")
    assert first == prepare(tmp_path / "second.json")
    assert first["issues"][0]["applied"]
    metrics = {r["Indicateur"]: r for r in first["bilans_finaux_apparies"]}
    assert metrics["Clients servis"]["Écart"] > 0
    assert metrics["Abandons"]["Écart"] < 0
    assert metrics["Niveau de service (%)"]["Avec décisions"] < 90
    assert metrics["Ressources mobilisées (caisse-min)"]["Écart"] > 0
    assert (tmp_path / "first.csv").exists()


def test_cached_geometry_does_not_share_cursors_between_sessions():
    result = ENGINE.run(CONFIG, BASE)
    first = studio_payload(result, "session_a", 0, {"time": 5})
    first["people"]["1"]["arrival_time"] = -100
    second = studio_payload(result, "session_b", 1, {"time": 9}, "message")
    assert first["cursor"] == {"time": 5}
    assert second["run_id"] == "session_b" and second["cursor"] == {"time": 9}
    assert second["people"]["1"]["arrival_time"] >= 0


def test_legacy_scene_keeps_its_original_queue_geometry():
    legacy, compact = SceneLayout(), SceneLayout(compact=True)
    assert legacy.queue_slot(1, 19).x == legacy.lane_x(1) + 3
    assert compact.queue_slot(1, 19).x < compact.lane_x(2)
