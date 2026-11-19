"""Exports du bilan dynamique à partir des mêmes tables que l'écran."""

import json
from dataclasses import asdict
from io import BytesIO

import pandas as pd
from openpyxl.styles import Font, PatternFill


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def experiment_payload(result, metrics: dict, actions: list) -> dict:
    return {
        "schema": "retailflow-experience/7.0",
        "perimetre": "Bilan final du moteur dynamique, temps en minutes",
        "indicateurs_finaux": metrics,
        "resultats_interventions": [asdict(outcome) for outcome in result.action_outcomes],
        "configuration": asdict(result.config),
        "options": asdict(result.options),
        "interventions": [asdict(action) for action in actions],
    }


def excel_bytes(tables: dict[str, pd.DataFrame], payload: dict) -> bytes:
    buffer = BytesIO()
    parameters = pd.DataFrame(
        [
            (key, json.dumps(value, ensure_ascii=False, allow_nan=False))
            for key, value in payload.items()
            if key != "indicateurs_finaux"
        ],
        columns=["Paramètre", "Valeur JSON"],
    )
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in {"Paramètres": parameters, **tables}.items():
            frame.to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                width = max(len(str(cell.value or "")) for cell in column)
                sheet.column_dimensions[column[0].column_letter].width = min(max(width + 3, 12), 48)
                column[0].fill = PatternFill("solid", fgColor="101F38")
                column[0].font = Font(color="FFFFFF", bold=True)
    return buffer.getvalue()
