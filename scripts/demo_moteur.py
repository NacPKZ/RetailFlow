"""Démo terminal du moteur : résumé des 3 scénarios pour les 2 comportements.

Lancement depuis la racine du dépôt :  python -m scripts.demo_moteur
"""

import statistics

from queuesmart.config import SCENARIOS
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import STRATEGIES, build_strategy

HEADER = (
    f"{'Scénario':<17}{'Comportement':<16}{'Caisses':>8}{'Clients':>8}"
    f"{'Attente moy.':>14}{'Attente max':>13}{'Fin':>8}"
)


def summary_line(result: SimulationResult) -> str:
    """Une ligne de tableau résumant une simulation (temps en minutes)."""
    waits = [customer.wait_time for customer in result.customers]
    config = result.config
    return (
        f"{config.name:<17}{result.strategy_name:<16}{config.open_registers:>8}"
        f"{config.customer_count:>8}{statistics.fmean(waits):>14.2f}"
        f"{max(waits):>13.2f}{result.end_time:>8.1f}"
    )


def main() -> None:
    print(HEADER)
    print("-" * len(HEADER))
    for config in SCENARIOS.values():
        for strategy_name in STRATEGIES:
            result = SimulationEngine(build_strategy(strategy_name)).run(config)
            print(summary_line(result))


if __name__ == "__main__":
    main()
