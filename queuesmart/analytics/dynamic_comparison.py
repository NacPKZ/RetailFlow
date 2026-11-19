"""Comparaison contrôlée de 1 à 5 caisses avec le moteur dynamique."""

from __future__ import annotations

from dataclasses import dataclass

from queuesmart.analytics.dynamic_kpi import DynamicKPICalculator, DynamicKPIReport
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import (
    DynamicOptions,
    DynamicResult,
    DynamicSimulationEngine,
)
from queuesmart.simulation.generator import CustomerGenerator


@dataclass(frozen=True)
class DynamicComparisonRow:
    register_count: int
    served_count: int
    abandoned_count: int
    abandonment_rate: float | None
    mean_wait_served_min: float | None
    p95_wait_served_min: float | None
    absolute_gain_vs_previous_min: float | None
    relative_gain_vs_previous: float | None


@dataclass(frozen=True)
class DynamicComparisonReport:
    base_config: ScenarioConfig
    options: DynamicOptions
    rows: tuple[DynamicComparisonRow, ...]
    results_by_register_count: dict[int, DynamicResult]
    reports_by_register_count: dict[int, DynamicKPIReport]


def compare_dynamic_register_counts(
    config: ScenarioConfig,
    options: DynamicOptions | None = None,
    max_registers: int = 5,
) -> DynamicComparisonReport:
    """Compare 1..``max_registers`` cash registers with identical customer samples.

    Comparisons require an integer seed and no scheduled register changes. A
    common fixed calendar can change the effective capacity differently when
    the initial number of open registers changes, so such comparisons are
    refused rather than described as equivalent.
    """
    if not 1 <= max_registers <= 5:
        raise ValueError("Le nombre maximal de caisses doit être compris entre 1 et 5.")
    if config.seed is None:
        raise ValueError(
            "Comparaison refusée : une graine fixe est nécessaire pour utiliser "
            "les mêmes clients."
        )

    selected_options = options or DynamicOptions()
    if selected_options.register_changes:
        raise ValueError(
            "Comparaison refusée : le calendrier de caisses peut modifier différemment "
            "la capacité effective selon le nombre initial de caisses."
        )

    baseline_customers = _customer_signature(config.with_registers(1))
    engine = DynamicSimulationEngine()
    calculator = DynamicKPICalculator()
    results: dict[int, DynamicResult] = {}
    reports: dict[int, DynamicKPIReport] = {}
    rows: list[DynamicComparisonRow] = []
    previous_mean: float | None = None

    for register_count in range(1, max_registers + 1):
        current_config = config.with_registers(register_count)
        if _customer_signature(current_config) != baseline_customers:
            raise RuntimeError(
                "Le générateur ne produit pas les mêmes clients pour les "
                "configurations comparées."
            )

        result = engine.run(current_config, selected_options)
        report = calculator.compute(result)
        current_mean = report.mean_wait_served_min
        absolute_gain = (
            previous_mean - current_mean
            if previous_mean is not None and current_mean is not None
            else None
        )
        relative_gain = (
            absolute_gain / previous_mean
            if absolute_gain is not None and previous_mean is not None and previous_mean > 0
            else None
        )
        rows.append(
            DynamicComparisonRow(
                register_count=register_count,
                served_count=report.served_count,
                abandoned_count=report.abandoned_count,
                abandonment_rate=report.abandonment_rate,
                mean_wait_served_min=current_mean,
                p95_wait_served_min=report.p95_wait_served_min,
                absolute_gain_vs_previous_min=absolute_gain,
                relative_gain_vs_previous=relative_gain,
            )
        )
        results[register_count] = result
        reports[register_count] = report
        previous_mean = current_mean

    return DynamicComparisonReport(
        base_config=config,
        options=selected_options,
        rows=tuple(rows),
        results_by_register_count=results,
        reports_by_register_count=reports,
    )


def _customer_signature(config: ScenarioConfig) -> tuple[tuple[int, float, float], ...]:
    customers = CustomerGenerator(config).generate()
    return tuple(
        (customer.customer_id, customer.arrival_time, customer.service_duration)
        for customer in customers
    )
