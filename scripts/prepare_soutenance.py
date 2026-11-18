"""Préparer un résultat de secours déterministe, sans démarrer Streamlit.

Depuis la racine : python scripts/prepare_soutenance.py
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from queuesmart.analytics.dynamic_metrics import paired_metrics  # noqa: E402
from queuesmart.analytics.interventions import Intervention, apply_interventions  # noqa: E402
from queuesmart.analytics.visual_data import customer_frame, flow_frame  # noqa: E402
from queuesmart.config import ScenarioConfig  # noqa: E402
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine  # noqa: E402


def prepare(output: Path) -> dict:
    config = ScenarioConfig("Soutenance reproductible", 110, 60.0, 1.7, 2, seed=42)
    options = DynamicOptions(patience_min=12.0, switching_enabled=True)
    engine = DynamicSimulationEngine()
    reference = engine.run(config, options)
    flow = flow_frame(customer_frame(reference))
    peak = float(flow.loc[flow["En attente"].idxmax(), "Minute"])
    action = Intervention(peak, "register", 3, opened=True)
    changed = engine.run(config, apply_interventions(options, [action]))
    payload = {
        "schema": "retailflow-soutenance/6.1",
        "configuration": asdict(config),
        "options": asdict(options),
        "minute_du_pic_temoin": peak,
        "intervention": asdict(action),
        "bilans_finaux_apparies": paired_metrics(reference, changed),
        "issues": [asdict(o) for o in changed.action_outcomes],
        "limites": "Une graine synthétique, effet combiné, aucune généralisation statistique.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    customer_frame(changed).to_csv(output.with_suffix(".csv"), index=False, sep=";", decimal=",")
    return payload


if __name__ == "__main__":
    destination = Path("docs/validation_v6_1/scenario_secours.json")
    prepare(destination)
    print(f"Résultats de secours : {destination}")
