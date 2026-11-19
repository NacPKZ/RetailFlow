"""Bilan final dynamique et ressources réellement mobilisées, sans mélange de moteurs."""

from queuesmart.analytics.visual_data import customer_frame, service_level
from queuesmart.simulation.dynamic import DynamicResult


def resource_frame(result: DynamicResult):
    """Intégrer les caisses ouvertes OU achevant un service, jusqu'à la dernière sortie.

    Une caisse fermée qui termine son client mobilise encore une ressource.
    Les commandes administratives après la dernière sortie n'allongent pas le bilan.
    """
    import pandas as pd

    horizon = max(
        (c.departure_time or c.abandoned_at or c.arrival_time for c in result.customers),
        default=0.0,
    )
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
    return {
        "Attente moyenne des servis (min)": float(served.mean()) if len(served) else None,
        "Médiane des servis (min)": float(served.median()) if len(served) else None,
        "P95 des servis (min)": float(served.quantile(0.95)) if len(served) else None,
        "Taux d'abandon (%)": 100 * result.abandoned_count / len(clients) if len(clients) else 0.0,
        "P90 des servis (min)": float(served.quantile(0.9)) if len(served) else None,
        "Clients servis": result.served_count,
        "Abandons": result.abandoned_count,
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
