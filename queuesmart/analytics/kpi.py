"""Indicateurs de qualité de service (KPI) d'une ou plusieurs simulations."""

import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from queuesmart.config import WAIT_THRESHOLD_MIN
from queuesmart.simulation.result import SimulationResult

DECILE_COUNT = 10  # le 9e et dernier décile est le 90e percentile


@dataclass(frozen=True)
class KpiReport:
    """Synthèse chiffrée d'une simulation (temps en minutes, parts entre 0 et 1)."""

    customer_count: int
    mean_wait: float
    median_wait: float
    p90_wait: float
    max_wait: float
    share_over_threshold: float  # part des clients attendant plus que le seuil
    mean_utilization: float
    utilization_by_register: dict[int, float]


class KpiCalculator:
    """Calcule les KPI. Le seuil d'attente « longue » est paramétrable."""

    def __init__(self, wait_threshold_min: float = WAIT_THRESHOLD_MIN) -> None:
        if wait_threshold_min < 0:
            raise ValueError("Le seuil d'attente ne peut pas être négatif.")
        self._wait_threshold_min = wait_threshold_min

    def compute(self, result: SimulationResult) -> KpiReport:
        """KPI d'une seule simulation."""
        return self.compute_many([result])

    def compute_many(self, results: Sequence[SimulationResult]) -> KpiReport:
        """KPI de plusieurs simulations : les attentes de tous les clients sont regroupées.

        Regrouper (plutôt que moyenner des p90) donne un p90 plus stable.
        """
        if not results:
            raise ValueError("Il faut au moins un résultat de simulation.")
        waits = sorted(customer.wait_time for result in results for customer in result.customers)
        utilization = _utilization_by_register(results)
        return KpiReport(
            customer_count=len(waits),
            mean_wait=statistics.fmean(waits),
            median_wait=statistics.median(waits),
            p90_wait=_percentile_90(waits),
            max_wait=waits[-1],
            share_over_threshold=self._share_over_threshold(waits),
            mean_utilization=statistics.fmean(utilization.values()),
            utilization_by_register=utilization,
        )

    def _share_over_threshold(self, waits: Sequence[float]) -> float:
        return sum(1 for wait in waits if wait > self._wait_threshold_min) / len(waits)


def _percentile_90(values: Sequence[float]) -> float:
    """90e percentile par interpolation linéaire (même convention que numpy)."""
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=DECILE_COUNT, method="inclusive")[-1]


def _utilization_by_register(results: Sequence[SimulationResult]) -> dict[int, float]:
    """Taux d'occupation de chaque caisse = temps de service / durée de la simulation.

    Avec plusieurs simulations, on prend la moyenne par caisse.
    """
    samples: dict[int, list[float]] = defaultdict(list)
    for result in results:
        for register in result.registers:
            samples[register.register_id].append(register.busy_time() / result.end_time)
    return {register_id: statistics.fmean(rates) for register_id, rates in sorted(samples.items())}
