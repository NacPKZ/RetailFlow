"""Mesures reproductibles du calcul, sans prétendre mesurer la fluidité du navigateur."""

import json
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from queuesmart.analytics.decision_lab import DecisionAssumptions, compare_dynamic_capacity
from queuesmart.config import ScenarioConfig
from queuesmart.scene.html import scene_data
from queuesmart.scene.layout import SceneLayout
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine


def main():
    rows = []
    for count in (100, 500):
        config = ScenarioConfig("Charge V7", count, 60, 1.7, 2, 42)
        options = DynamicOptions()
        start = perf_counter()
        result = DynamicSimulationEngine().run(config, options)
        engine_ms = (perf_counter() - start) * 1000
        start = perf_counter()
        payload = scene_data(result, SceneLayout(compact=True))
        scene_ms = (perf_counter() - start) * 1000
        start = perf_counter()
        summary, trials = compare_dynamic_capacity(config, options, DecisionAssumptions(), 5, 5)
        lab_ms = (perf_counter() - start) * 1000
        rows.append(
            {
                "clients": count,
                "events": len(result.events),
                "engine_ms": engine_ms,
                "scene_ms": scene_ms,
                "scene_json_bytes": len(json.dumps(payload).encode()),
                "lab_5x5_ms": lab_ms,
                "capacity_rows": len(summary),
                "trials": len(trials),
                "conservation": result.served_count + result.abandoned_count == count,
                "reproducible": result == DynamicSimulationEngine().run(replace(config), options),
            }
        )
    print(
        json.dumps(
            {
                "scope": "Calcul Python, hors navigateur, un passage par configuration",
                "measurements": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
