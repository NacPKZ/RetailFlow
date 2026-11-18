"""Microbenchmark reproductible du moteur et de la préparation des trajectoires.

Utilisation : python scripts/benchmark_v61.py chemin_resultat.json
Les mesures n'incluent pas le rendu du navigateur ni le réseau.
"""

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from queuesmart.config import ScenarioConfig  # noqa: E402
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine  # noqa: E402
from queuesmart.ui.studio_component import studio_payload  # noqa: E402


def benchmark():
    rows = []
    for count in [10, 60, 100, 110]:
        for registers in range(1, 6):
            config = ScenarioConfig("Performance", count, 30.0, 2.0, registers, seed=42)
            samples = []
            for _ in range(3):
                start = time.perf_counter()
                result = DynamicSimulationEngine().run(config, DynamicOptions())
                samples.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            payload = studio_payload(result, "benchmark", 0, {})
            elapsed = (time.perf_counter() - start) * 1000
            warm_start = time.perf_counter()
            studio_payload(result, "benchmark", 0, {})
            warm_ms = (time.perf_counter() - warm_start) * 1000
            rows.append(
                {
                    "clients": count,
                    "caisses": registers,
                    "moteur_mediane_ms": statistics.median(samples),
                    "preparation_scene_ms": elapsed,
                    "scene_cache_chaud_ms": warm_ms,
                    "payload_octets": len(json.dumps(payload).encode()),
                }
            )
    return rows


if __name__ == "__main__":
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/retailflow_benchmark.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(benchmark(), indent=2) + "\n")
    print(output)
