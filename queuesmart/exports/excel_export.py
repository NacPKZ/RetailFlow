"""Export Excel du dashboard dynamique : six onglets avec métadonnées."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from queuesmart.analytics.dynamic_comparison import DynamicComparisonReport
from queuesmart.analytics.dynamic_kpi import DynamicKPIReport
from queuesmart.analytics.dynamic_optimizer import DynamicRecommendation
from queuesmart.exports.csv_export import _kpi_rows
from queuesmart.simulation.dynamic import DynamicResult

ENGINE_VERSION = "Version non déclarée dans le dépôt ; code source local"


def build_dynamic_excel_export(
    result: DynamicResult,
    report: DynamicKPIReport,
    comparison: DynamicComparisonReport | None = None,
    recommendation: DynamicRecommendation | None = None,
) -> bytes:
    """Génère le classeur contractuel et retourne ses octets XLSX."""
    workbook = Workbook()
    sheets = ["Paramètres", "Résumé KPI", "Caisses", "Clients", "Événements", "Comparaison"]
    worksheets = [workbook.active, *(workbook.create_sheet(name) for name in sheets[1:])]
    for sheet, name in zip(worksheets, sheets, strict=True):
        sheet.title = name

    _write_table(worksheets[0], _parameters(result, recommendation))
    _write_table(worksheets[1], _kpi_table(report))
    _write_table(worksheets[2], _register_table(report))
    _write_table(worksheets[3], _customer_table(report))
    _write_table(worksheets[4], _event_table(result))
    _write_table(worksheets[5], _comparison_table(comparison, recommendation))
    for sheet in worksheets:
        _format_sheet(sheet)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _parameters(result, recommendation) -> list[tuple[str, object]]:
    options, config = result.options, result.config
    return [
        ("Métadonnée", "Valeur"), ("Produit", "RetailFlow"),
        ("Package Python", "queuesmart"), ("Graine", config.seed),
        ("Hypothèses", "Clients synthétiques ; arrivées uniformes ; durées gamma."),
        ("Affectation", "Caisse ouverte à attente minimale ; départage par identifiant."),
        ("Patience (min)", options.patience_min),
        ("Changements de file", options.switching_enabled),
        ("Intervalle de réévaluation (min)", options.switching_interval_min),
        ("Gain minimal (min)", options.switching_gain_min),
        ("Calendrier caisses", repr(options.register_changes)),
        ("Seuil d'attente (min)", recommendation.threshold_min if recommendation else None),
        ("Caisses recommandées", recommendation.recommended_registers if recommendation else None),
        ("Version moteur", ENGINE_VERSION),
        ("Date génération", datetime.now().astimezone().isoformat(timespec="seconds")),
        (
            "Limites",
            "Simulation pédagogique ; pas de coût personnel ; résultats après simulation.",
        ),
    ]


def _kpi_table(report) -> list[tuple]:
    headers = ("Indicateur", "Valeur", "Unité", "Population", "Formule / méthode", "Fenêtre")
    rows = [headers]
    rows.extend(
        (
            metric["metric"], metric["value"], metric["unit"], metric["population"],
            f'{metric["formula"]} — {metric["method"]}', metric["observation_window"],
        )
        for metric in _kpi_rows(report)
    )
    return rows


def _register_table(report) -> list[tuple]:
    rows = [
        ("Caisse", "Servis", "Attente moyenne (min)", "Service (min)",
         "Ouverte (min)", "Disponible (min)", "Occupation (%)", "Pic file")
    ]
    rows.extend(
        (
            register.register_id, register.served_count, register.mean_wait_served_min,
            register.total_service_time_min, register.open_time_min,
            register.available_time_min, register.utilization_rate,
            register.peak_queue_length,
        )
        for register in report.registers
    )
    return rows


def _customer_table(report) -> list[tuple]:
    fields = tuple(report.customer_rows[0]) if report.customer_rows else (
        "customer_id", "arrival_time_min", "register_id", "service_duration_min",
        "service_start_min", "departure_time_min", "abandoned_at_min", "outcome",
        "wait_served_min", "time_before_abandonment_min", "total_time_in_system_min",
    )
    return [fields, *(tuple(row.get(field) for field in fields) for row in report.customer_rows)]


def _event_table(result) -> list[tuple]:
    headers = (
        "Ordre", "Temps (min)", "Type", "Client", "Caisse source",
        "Caisse cible", "Position file",
    )
    rows = [headers]
    rows.extend(
        (i, event.time, event.type, event.customer_id, event.register_id,
         event.target_register_id, event.queue_position)
        for i, event in enumerate(result.events)
    )
    return rows


def _comparison_table(comparison, recommendation) -> list[tuple]:
    rows = [
        ("Caisses", "Servis", "Abandons", "Taux abandon", "Attente moyenne (min)",
         "P95 (min)", "Gain absolu (min)", "Gain relatif")
    ]
    if comparison:
        rows.extend(
            (
                row.register_count, row.served_count, row.abandoned_count,
                row.abandonment_rate, row.mean_wait_served_min,
                row.p95_wait_served_min, row.absolute_gain_vs_previous_min,
                row.relative_gain_vs_previous,
            )
            for row in comparison.rows
        )
    if recommendation:
        rows.extend(
            ((), ("Seuil (min)", recommendation.threshold_min),
             ("Recommandation", recommendation.message))
        )
    return rows


def _write_table(sheet, rows: list[tuple]) -> None:
    for row in rows:
        sheet.append(row)


def _format_sheet(sheet) -> None:
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="203A5B")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for column in sheet.columns:
        letter = get_column_letter(column[0].column)
        width = max((len(str(c.value)) for c in column if c.value is not None), default=8)
        sheet.column_dimensions[letter].width = min(max(width + 2, 12), 48)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if isinstance(cell.value, float):
                cell.number_format = "0.00"
    percent_columns = {"Caisses": (7,), "Comparaison": (4, 8)}
    for column in percent_columns.get(sheet.title, ()):
        for row in range(2, sheet.max_row + 1):
            sheet.cell(row, column).number_format = "0.0%"
    if sheet.title == "Résumé KPI":
        for row in range(2, sheet.max_row + 1):
            if sheet.cell(row, 3).value == "%":
                sheet.cell(row, 2).number_format = "0.0%"
