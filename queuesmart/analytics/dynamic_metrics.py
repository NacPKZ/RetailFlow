"""Bilan final dynamique et ressources réellement mobilisées, sans mélange de moteurs."""

import pandas as pd

from queuesmart.analytics.visual_data import customer_frame, service_level
from queuesmart.simulation.dynamic import DynamicResult


def observation_end(result: DynamicResult) -> float:
    terminal = [
        c.departure_time if c.departure_time is not None else c.abandoned_at
        for c in result.customers
    ]
    if any(t is None for t in terminal):
        # Un rejeu partiel se termine au dernier événement disponible.
        return result.events[-1].time if result.events else 0.0
    return max(terminal, default=0.0)


def resource_frame(result: DynamicResult):
    """Intégrer les caisses ouvertes OU achevant un service, jusqu'à la dernière sortie.

    Une caisse fermée qui termine son client mobilise encore une ressource.
    Les commandes administratives après la dernière sortie n'allongent pas le bilan.
    """
    horizon = observation_end(result)
    opened = {r: r <= result.config.open_registers for r in range(1, 6)}
    serving = dict.fromkeys(opened)
    available = dict.fromkeys(opened, 0.0)
    busy = dict.fromkeys(opened, 0.0)
    previous = 0.0
    for event in result.events:
        time = min(event.time, horizon)
        for rid in opened:
            available[rid] += (time - previous) * (opened[rid] or serving[rid] is not None)
            busy[rid] += (time - previous) * (serving[rid] is not None)
        previous = time
        rid = event.register_id
        if event.type in ("register_opened", "register_closed"):
            opened[rid] = event.type == "register_opened"
        elif event.type == "service_started":
            serving[rid] = event.customer_id
        elif event.type == "customer_departed":
            serving[rid] = None
        if event.time >= horizon:
            break
    for rid in opened:
        available[rid] += (horizon - previous) * (opened[rid] or serving[rid] is not None)
        busy[rid] += (horizon - previous) * (serving[rid] is not None)
    return pd.DataFrame(
        [
            {
                "Caisse": rid,
                "Service (min)": busy[rid],
                "Mobilisation (min)": available[rid],
                "Occupation (%)": 100 * busy[rid] / available[rid] if available[rid] else None,
            }
            for rid in opened
        ]
    )


def final_metrics(result: DynamicResult) -> dict[str, float | int | None]:
    clients = customer_frame(result)
    served = clients.loc[clients["Statut"] == "Servi", "Attente"]
    resources = resource_frame(result)
    denominator = resources["Mobilisation (min)"].sum()
    finished = clients.loc[clients["Statut"] == "Servi"]
    abandoned = clients.loc[clients["Statut"] == "Abandon"]
    horizon = observation_end(result)

    def mean(values):
        return float(values.mean()) if len(values) else None

    return {
        "Clients arrivés": len(clients),
        "Clients encore présents": len(clients) - len(finished) - len(abandoned),
        "Fin d’observation (min)": horizon,
        "Attente moyenne des servis (min)": mean(served),
        "Médiane des servis (min)": float(served.median()) if len(served) else None,
        "P95 des servis (min)": float(served.quantile(0.95)) if len(served) else None,
        "Taux d'abandon (%)": 100 * result.abandoned_count / len(clients) if len(clients) else 0.0,
        "P90 des servis (min)": float(served.quantile(0.9)) if len(served) else None,
        "Attente maximale des servis (min)": float(served.max()) if len(served) else None,
        "Service moyen des servis (min)": mean(finished["Service"]),
        "Temps dans le système des servis (min)": mean(finished["Sortie"] - finished["Arrivée"]),
        "Temps moyen avant abandon (min)": mean(abandoned["Attente"]),
        "Débit (servis/min)": len(finished) / horizon if horizon else None,
        "Clients servis": len(finished),
        "Abandons": len(abandoned),
        "Niveau de service (%)": service_level(clients),
        "Occupation des ressources (%)": (
            100 * float(resources["Service (min)"].sum()) / denominator if denominator else None
        ),
        "Ressources mobilisées (caisse-min)": float(denominator),
    }


def paired_metrics(reference: DynamicResult, changed: DynamicResult) -> list[dict]:
    before, after = final_metrics(reference), final_metrics(changed)
    return [
        {
            "Indicateur": key,
            "Témoin": value,
            "Avec décisions": after[key],
            "Écart": after[key] - value if value is not None and after[key] is not None else None,
        }
        for key, value in before.items()
    ]
