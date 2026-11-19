"""Alertes analytiques calculées sur le résultat complet d'une simulation dynamique."""

from __future__ import annotations

from queuesmart.analytics.dynamic_kpi import DynamicKPIReport, DynamicQueuePoint


def build_dynamic_alerts(
    report: DynamicKPIReport,
    max_queue: int = 5,
    max_estimated_wait_min: float = 5.0,
    abandonment_limit: float = 0.10,
    occupancy_limit: float = 0.85,
) -> list[dict[str, object]]:
    """Crée une alerte par période continue de dépassement, sans doublonner les instants."""
    if max_queue < 1:
        raise ValueError("Le seuil de longueur de file doit être au moins égal à 1.")
    if max_estimated_wait_min < 0:
        raise ValueError("Le seuil d'attente estimée doit être positif ou nul.")
    if not 0 <= abandonment_limit <= 1 or not 0 <= occupancy_limit <= 1:
        raise ValueError("Les seuils de taux doivent être compris entre 0 et 1.")

    alerts: list[dict[str, object]] = []
    for register_id in range(1, 6):
        points = [
            point for point in report.queue_timeline if point.register_id == register_id
        ]
        alerts.extend(
            _threshold_spans(
                points,
                register_id,
                "File d'attente trop longue",
                max_queue,
                lambda point: point.waiting_count,
                "clients en attente",
            )
        )
        alerts.extend(
            _threshold_spans(
                points,
                register_id,
                "Attente estimée excessive pour la dernière position",
                max_estimated_wait_min,
                lambda point: point.estimated_wait_last_customer_min,
                "min estimées",
            )
        )

    if report.abandonment_rate is not None and report.abandonment_rate >= abandonment_limit:
        alerts.append(
            {
                "Alerte": "Taux d'abandon élevé",
                "Caisse": "Toutes",
                "Début (min)": report.observation_start_min,
                "Fin (min)": report.observation_end_min,
                "Critère déclencheur": (
                    f"{report.abandonment_rate:.1%} ≥ {abandonment_limit:.1%} des arrivées"
                ),
            }
        )

    for register in report.registers:
        if register.utilization_rate is not None and register.utilization_rate >= occupancy_limit:
            alerts.append(
                {
                    "Alerte": "Occupation soutenue sur la fenêtre",
                    "Caisse": f"Caisse {register.register_id}",
                    "Début (min)": report.observation_start_min,
                    "Fin (min)": report.observation_end_min,
                    "Critère déclencheur": (
                        f"{register.utilization_rate:.1%} ≥ {occupancy_limit:.1%} "
                        "du temps disponible effectif"
                    ),
                }
            )
    return alerts


def _threshold_spans(
    points: list[DynamicQueuePoint],
    register_id: int,
    label: str,
    threshold: float,
    value_getter,
    unit: str,
) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    span_start: float | None = None
    span_end: float | None = None
    span_value: float | None = None

    for point in points:
        value = value_getter(point)
        if value >= threshold:
            if span_start is None:
                span_start = point.time_min
                span_value = value
            span_end = point.time_min
            span_value = max(span_value, value)
        elif span_start is not None:
            alerts.append(
                _alert_row(
                    label, register_id, span_start, point.time_min, span_value, threshold, unit
                )
            )
            span_start = None
            span_end = None
            span_value = None

    if span_start is not None:
        alerts.append(
            _alert_row(label, register_id, span_start, span_end, span_value, threshold, unit)
        )
    return alerts


def _alert_row(
    label: str,
    register_id: int,
    start: float,
    end: float | None,
    observed: float | None,
    threshold: float,
    unit: str,
) -> dict[str, object]:
    return {
        "Alerte": label,
        "Caisse": f"Caisse {register_id}",
        "Début (min)": start,
        "Fin (min)": end,
        "Critère déclencheur": f"maximum observé {observed:g} ≥ seuil {threshold:g} {unit}",
    }
