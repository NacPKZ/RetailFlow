"""Exports CSV UTF-8 des résultats du moteur dynamique."""

from __future__ import annotations

import csv
import io
from typing import Any

from queuesmart.analytics.dynamic_comparison import DynamicComparisonReport
from queuesmart.analytics.dynamic_kpi import DynamicKPIReport
from queuesmart.simulation.dynamic import DynamicResult

CSV_FIELDS = {
    "clients.csv": (
        "customer_id", "arrival_time_min", "register_id", "service_duration_min",
        "service_start_min", "departure_time_min", "abandoned_at_min", "outcome",
        "wait_served_min", "time_before_abandonment_min", "total_time_in_system_min",
    ),
    "evenements.csv": (
        "event_order", "time_min", "type", "customer_id", "register_id",
        "target_register_id", "queue_position",
    ),
    "caisses.csv": (
        "register_id", "served_count", "mean_wait_served_min", "total_service_time_min",
        "open_time_min", "available_time_min", "utilization_rate", "peak_queue_length",
    ),
    "kpi.csv": (
        "metric", "value", "unit", "population", "formula", "observation_window", "method",
    ),
    "comparaison.csv": (
        "register_count", "served_count", "abandoned_count", "abandonment_rate",
        "mean_wait_served_min", "p95_wait_served_min", "absolute_gain_vs_previous_min",
        "relative_gain_vs_previous",
    ),
}


def build_dynamic_csv_exports(
    result: DynamicResult,
    report: DynamicKPIReport,
    comparison: DynamicComparisonReport | None = None,
) -> dict[str, bytes]:
    """Construit les cinq CSV contractuels, même si certaines tables sont vides."""
    events = [{"event_order": i, **event.to_dict()} for i, event in enumerate(result.events)]
    registers = [vars(register) for register in report.registers]
    comparisons = [vars(row) for row in comparison.rows] if comparison else []
    tables = {
        "clients.csv": report.customer_rows,
        "evenements.csv": events,
        "caisses.csv": registers,
        "kpi.csv": _kpi_rows(report),
        "comparaison.csv": comparisons,
    }
    return {name: _csv_bytes(rows, CSV_FIELDS[name]) for name, rows in tables.items()}


def _kpi_rows(report: DynamicKPIReport) -> list[dict[str, Any]]:
    """Dictionnaire KPI exportable : formule, population, fenêtre et méthode."""
    definitions = [
        (
            'arrivals',
            report.arrival_count,
            'clients',
            'Tous',
            "Nombre d'arrivées",
            'Simulation complète',
            'Comptage',
        ),
        (
            'served',
            report.served_count,
            'clients',
            'Servis',
            'Nombre de servis',
            'Simulation complète',
            'Comptage',
        ),
        (
            'abandoned',
            report.abandoned_count,
            'clients',
            'Abandons',
            'Nombre d’abandons',
            'Simulation complète',
            'Comptage',
        ),
        (
            'mean_wait_served',
            report.mean_wait_served_min,
            'min',
            'Servis',
            'Moyenne(service_start - arrivée)',
            'Arrivée au début de service',
            'Moyenne',
        ),
        (
            'median_wait_served',
            report.median_wait_served_min,
            'min',
            'Servis',
            'Médiane(service_start - arrivée)',
            'Arrivée au début de service',
            'Médiane',
        ),
        (
            'p90_wait_served',
            report.p90_wait_served_min,
            'min',
            'Servis',
            'P90(service_start - arrivée)',
            'Arrivée au début de service',
            'Quantile linéaire inclusif',
        ),
        (
            'p95_wait_served',
            report.p95_wait_served_min,
            'min',
            'Servis',
            'P95(service_start - arrivée)',
            'Arrivée au début de service',
            'Quantile linéaire inclusif',
        ),
        (
            'max_wait_served',
            report.max_wait_served_min,
            'min',
            'Servis',
            'Max(service_start - arrivée)',
            'Arrivée au début de service',
            'Maximum',
        ),
        (
            'mean_service_duration_served',
            report.mean_service_duration_served_min,
            'min',
            'Servis',
            'Moyenne(service_duration)',
            'Services terminés',
            'Moyenne',
        ),
        (
            'mean_total_time_served',
            report.mean_total_time_served_min,
            'min',
            'Servis',
            'Moyenne(départ - arrivée)',
            'Arrivée au départ',
            'Moyenne',
        ),
        (
            'total_time_served_customer',
            report.total_time_served_customer_min,
            'client-min',
            'Servis',
            'Somme(départ - arrivée)',
            'Arrivée au départ',
            'Somme',
        ),
        (
            'abandonment_rate',
            report.abandonment_rate,
            '%',
            'Arrivés',
            'Abandons / arrivées',
            'Simulation complète',
            'Proportion 0-1',
        ),
        (
            'mean_time_before_abandonment',
            report.mean_time_before_abandonment_min,
            'min',
            'Abandons',
            'Moyenne(abandon - arrivée)',
            'Arrivée à abandon',
            'Moyenne',
        ),
        (
            'throughput_served',
            report.throughput_served_per_min,
            'clients/min',
            'Servis',
            'Servis / durée observée',
            'Première arrivée au dernier départ/abandon',
            'Débit',
        ),
        (
            'flow_observation_points',
            len(report.flow_timeline),
            'instants',
            'Événements',
            'Nombre d’états observés',
            'Événements groupés par temps',
            'Comptage',
        ),
        (
            'flow_conservation_valid',
            all(p.is_conserved for p in report.flow_timeline),
            'booléen',
            'Instants observés',
            'Arrivés = terminés + abandons + attente + service',
            'Après événements simultanés',
            'Vrai si conservation respectée',
        ),
    ]
    return [dict(zip(CSV_FIELDS["kpi.csv"], row, strict=True)) for row in definitions]


def _csv_bytes(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")
