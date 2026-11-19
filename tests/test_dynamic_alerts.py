"""Tests du regroupement des alertes en périodes continues."""

from dataclasses import replace

import pytest

from queuesmart.analytics.dynamic_alerts import build_dynamic_alerts
from queuesmart.analytics.dynamic_kpi import (
    DynamicKPICalculator,
    DynamicKPIReport,
    DynamicQueuePoint,
    DynamicRegisterKPI,
)
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicResult


def build_report() -> DynamicKPIReport:
    config = ScenarioConfig("Alertes", 1, 10.0, 2.0, 1, seed=42)
    result = DynamicResult(config, DynamicOptions(), (), ())
    base_report = DynamicKPICalculator().compute(result)
    queue_points = (
        DynamicQueuePoint(0.0, 1, 0, 0, True, 0.0),
        DynamicQueuePoint(1.0, 1, 2, 1, True, 6.0),
        DynamicQueuePoint(2.0, 1, 3, 1, True, 7.0),
        DynamicQueuePoint(3.0, 1, 0, 0, True, 0.0),
        DynamicQueuePoint(4.0, 1, 2, 1, True, 10.0),
    )
    registers = tuple(
        DynamicRegisterKPI(
            register_id=register_id,
            served_count=1 if register_id == 1 else 0,
            mean_wait_served_min=1.0 if register_id == 1 else None,
            total_service_time_min=9.0 if register_id == 1 else 0.0,
            open_time_min=10.0 if register_id == 1 else 0.0,
            available_time_min=10.0 if register_id == 1 else 0.0,
            utilization_rate=0.9 if register_id == 1 else None,
            peak_queue_length=3 if register_id == 1 else 0,
        )
        for register_id in range(1, 6)
    )
    return replace(
        base_report,
        abandonment_rate=0.2,
        observation_start_min=0.0,
        observation_end_min=4.0,
        queue_timeline=queue_points,
        registers=registers,
    )


def test_alerts_are_grouped_by_continuous_period_and_include_all_requested_criteria():
    alerts = build_dynamic_alerts(
        build_report(),
        max_queue=2,
        max_estimated_wait_min=5.0,
        abandonment_limit=0.1,
        occupancy_limit=0.85,
    )

    queue_alerts = [alert for alert in alerts if alert["Alerte"] == "File d'attente trop longue"]
    wait_alerts = [
        alert
        for alert in alerts
        if alert["Alerte"] == "Attente estimée excessive pour la dernière position"
    ]
    assert len(queue_alerts) == 2
    assert queue_alerts[0]["Début (min)"] == 1.0
    assert queue_alerts[0]["Fin (min)"] == 3.0
    assert "maximum observé 3" in queue_alerts[0]["Critère déclencheur"]
    assert len(wait_alerts) == 2
    assert any(alert["Alerte"] == "Taux d'abandon élevé" for alert in alerts)
    assert any(alert["Alerte"] == "Occupation soutenue sur la fenêtre" for alert in alerts)


def test_alert_thresholds_are_validated():
    with pytest.raises(ValueError):
        build_dynamic_alerts(build_report(), max_queue=0)
    with pytest.raises(ValueError):
        build_dynamic_alerts(build_report(), abandonment_limit=1.1)
