"""Tests des exports CSV et Excel, dont le cas sans client servi (A09)."""

import csv
from io import BytesIO, StringIO

from openpyxl import load_workbook

from queuesmart.analytics.dynamic_comparison import compare_dynamic_register_counts
from queuesmart.analytics.dynamic_kpi import DynamicKPICalculator
from queuesmart.analytics.dynamic_optimizer import recommend_by_mean_wait
from queuesmart.config import ScenarioConfig
from queuesmart.exports.csv_export import build_dynamic_csv_exports
from queuesmart.exports.excel_export import build_dynamic_excel_export
from queuesmart.simulation.dynamic import (
    DynamicCustomerResult,
    DynamicEvent,
    DynamicOptions,
    DynamicResult,
    DynamicSimulationEngine,
)


def test_a09_csv_and_excel_exports_can_be_reimported_with_consistent_totals():
    config = ScenarioConfig("Export", 12, 20.0, 2.0, 2, seed=42)
    options = DynamicOptions(patience_min=5.0, switching_enabled=False)
    result = DynamicSimulationEngine().run(config, options)
    report = DynamicKPICalculator().compute(result)
    comparison = compare_dynamic_register_counts(config, options)
    recommendation = recommend_by_mean_wait(comparison, threshold_min=3.0)

    csv_files = build_dynamic_csv_exports(result, report, comparison)

    assert set(csv_files) == {
        "clients.csv",
        "evenements.csv",
        "caisses.csv",
        "kpi.csv",
        "comparaison.csv",
    }
    clients = list(csv.DictReader(StringIO(csv_files["clients.csv"].decode("utf-8"))))
    events = list(csv.DictReader(StringIO(csv_files["evenements.csv"].decode("utf-8"))))
    comparisons = list(
        csv.DictReader(StringIO(csv_files["comparaison.csv"].decode("utf-8")))
    )
    assert len(clients) == len(result.customers)
    assert len(events) == len(result.events)
    assert len(comparisons) == 5

    excel_bytes = build_dynamic_excel_export(result, report, comparison, recommendation)
    workbook = load_workbook(BytesIO(excel_bytes), data_only=True)

    assert workbook.sheetnames == [
        "Paramètres",
        "Résumé KPI",
        "Caisses",
        "Clients",
        "Événements",
        "Comparaison",
    ]
    assert workbook["Clients"].max_row == len(result.customers) + 1
    assert workbook["Événements"].max_row == len(result.events) + 1
    assert workbook["Comparaison"].max_row == 9
    assert workbook["Paramètres"].cell(4, 2).value == 42
    assert "non déclarée" in workbook["Paramètres"].cell(14, 2).value.lower()


def test_exports_handle_a_result_with_no_served_customer():
    config = ScenarioConfig("Abandons", 2, 10.0, 2.0, 1, seed=42)
    options = DynamicOptions(patience_min=0.01, switching_enabled=False)
    customers = (
        DynamicCustomerResult(1, 0.0, 2.0, 1, None, None, 1.0),
        DynamicCustomerResult(2, 0.5, 2.0, 1, None, None, 1.5),
    )
    events = (
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.5, "customer_arrived", 2),
        DynamicEvent(0.5, "queue_joined", 2, 1, queue_position=2),
        DynamicEvent(1.0, "customer_abandoned", 1, 1),
        DynamicEvent(1.5, "customer_abandoned", 2, 1),
    )
    result = DynamicResult(config, options, events, customers)
    report = DynamicKPICalculator().compute(result)

    assert report.served_count == 0
    assert report.mean_wait_served_min is None

    csv_files = build_dynamic_csv_exports(result, report)
    kpi_rows = list(csv.DictReader(StringIO(csv_files["kpi.csv"].decode("utf-8"))))
    mean_wait_row = next(row for row in kpi_rows if row["metric"] == "mean_wait_served")
    assert mean_wait_row["value"] == ""

    excel_bytes = build_dynamic_excel_export(result, report)
    workbook = load_workbook(BytesIO(excel_bytes), data_only=True)
    summary = workbook["Résumé KPI"]
    mean_wait_row_number = next(
        row_number
        for row_number in range(2, summary.max_row + 1)
        if summary.cell(row_number, 1).value == "mean_wait_served"
    )
    assert summary.cell(mean_wait_row_number, 2).value is None
