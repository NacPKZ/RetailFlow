"""Générer les résultats finaux de démonstration, sans interface ni accès réseau."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from queuesmart.analytics.decision_lab import (
    DecisionAssumptions,
    compare_dynamic_capacity,
    decision_report,
)
from queuesmart.analytics.dynamic_metrics import final_metrics
from queuesmart.analytics.interventions import Intervention, apply_interventions
from queuesmart.analytics.visual_data import customer_frame
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine

out = Path("docs/demonstration")
out.mkdir(exist_ok=True)
options = DynamicOptions()
engine = DynamicSimulationEngine()
rows = []
for name, count, capacity in [
    ("A_normal", 50, 3),
    ("B_pointe", 110, 4),
    ("C_sous_capacite", 110, 2),
    ("D_intervention", 110, 2),
]:
    config = ScenarioConfig(name, count, 60, 1.7, capacity, 42)
    opts = (
        apply_interventions(options, [Intervention(20, "register", 3, opened=True)])
        if name.startswith("D")
        else options
    )
    result = engine.run(config, opts)
    row = {
        "scenario": name,
        "configuration": asdict(config),
        "options": asdict(opts),
        "resultats": final_metrics(result),
    }
    rows.append(row)
    customer_frame(result).to_csv(
        out / f"{name}.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig"
    )
(out / "scenarios.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=False))
config = ScenarioConfig("E_comparaison", 110, 60, 1.7, 2, 42)
a = DecisionAssumptions()
summary, trials = compare_dynamic_capacity(config, options, a, 5, 5)
summary.to_csv(out / "E_capacites.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
trials.to_csv(out / "E_tirages.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
(out / "E_rapport.md").write_text(decision_report(config, options, a, summary, trials))
print(json.dumps(rows, ensure_ascii=False, indent=2))
