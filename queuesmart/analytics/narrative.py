"""Commentaires déterministes chiffrés, liés au périmètre de chaque analyse."""

from queuesmart.analytics.visual_data import customer_frame, flow_frame, service_level
from queuesmart.simulation.dynamic import DynamicResult
from queuesmart.simulation.result import SimulationResult


def describe_result(result: SimulationResult | DynamicResult) -> list[tuple[str, str]]:
    clients = customer_frame(result)
    flow = flow_frame(clients)
    peak = flow.loc[flow["En attente"].idxmax()]
    served = clients.loc[clients["Statut"] == "Servi"]
    abandoned = int((clients["Statut"] == "Abandon").sum())
    level = service_level(clients)
    mean = float(served["Attente"].mean()) if len(served) else None
    summary = (
        f"{len(served)} clients sur {len(clients)} sont servis ; {abandoned} abandonnent. "
        f"{level:.1f} % des arrivants sont servis avec une attente d'au plus 5 minutes."
    )
    if mean is not None:
        summary += f" L'attente moyenne des clients servis est de {mean:.2f} min."
    pressure = (
        f"La file atteint {int(peak['En attente'])} clients à la minute {peak['Minute']:.2f}. "
        "Ce maximum porte sur les clients qui attendent, sans inclure ceux en service."
    )
    bins = clients.assign(tranche=(clients["Arrivée"] // 10 * 10).astype(int))
    busiest = bins.groupby("tranche").size()
    start = int(busiest.idxmax())
    arrivals = (
        f"La tranche de {start} à {start + 10} min reçoit {int(busiest.max())} arrivants, "
        f"soit {100 * busiest.max() / len(clients):.1f} % du scénario. "
        "L'arrivée des clients est simulée et ne représente pas un magasin réel."
    )
    recommendation = (
        "La cible de service est atteinte dans ce scénario. Compare plusieurs graines "
        "avant de réduire la capacité."
        if level >= 90
        else "La cible de 90 % n'est pas atteinte. Teste l'ouverture d'une caisse avant le pic "
        "puis compare à la référence avec la même graine."
    )
    return [
        ("Diagnostic", summary),
        ("Point de tension", pressure),
        ("Affluence", arrivals),
        ("Piste à tester", recommendation),
    ]


def compare_results(reference: DynamicResult, changed: DynamicResult) -> dict[str, float]:
    before, after = customer_frame(reference), customer_frame(changed)
    return {
        "Niveau de service (points)": float(service_level(after) - service_level(before)),
        "Clients servis": changed.served_count - reference.served_count,
        "Abandons": changed.abandoned_count - reference.abandoned_count,
        "Attente totale (min)": float(after["Attente"].sum() - before["Attente"].sum()),
    }
