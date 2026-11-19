"""Commandes interactives validées sur l'état réel du moteur, jamais sur le dessin."""

import math
from dataclasses import dataclass, replace
from typing import Any

from queuesmart.simulation.dynamic import DynamicOptions, DynamicResult


@dataclass(frozen=True)
class Intervention:
    time: float
    kind: str
    register_id: int
    customer_id: int | None = None
    opened: bool | None = None


def state_at(result: DynamicResult, time: float) -> dict[str, Any]:
    queues = {r: [] for r in range(1, 6)}
    opened = {r: r <= result.config.open_registers for r in queues}
    serving = dict.fromkeys(queues)
    for event in result.events:
        if event.time > time:
            break
        rid, cid = event.register_id, event.customer_id
        if event.type == "queue_joined":
            queues[rid].append(cid)
        elif event.type == "service_started":
            queues[rid].remove(cid)
            serving[rid] = cid
        elif event.type == "customer_departed":
            serving[rid] = None
        elif event.type == "customer_abandoned":
            queues[rid].remove(cid)
        elif event.type == "queue_switched":
            queues[rid].remove(cid)
            queues[event.target_register_id].append(cid)
        elif event.type in ("register_opened", "register_closed"):
            opened[rid] = event.type == "register_opened"
    return {"queues": queues, "opened": opened, "serving": serving}


def validate_intervention(result: DynamicResult, payload: dict) -> Intervention:
    """Refuser explicitement les actions impossibles ou les valeurs malformées."""
    try:
        time = float(payload["time"])
        rid = payload["register_id"]
        kind = payload["kind"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Commande incomplète.") from error
    horizon = max(e.time for e in result.events)
    if not math.isfinite(time) or not 0 <= time <= horizon:
        raise ValueError("L'instant choisi est hors de la simulation.")
    if type(rid) is not int or not 1 <= rid <= 5:
        raise ValueError("Cette caisse n'existe pas.")
    state = state_at(result, time)
    if kind == "register":
        opened = payload.get("opened")
        if type(opened) is not bool:
            raise ValueError("L'état de caisse doit être ouvert ou fermé.")
        if state["opened"][rid] == opened:
            raise ValueError("La caisse est déjà dans cet état.")
        if not opened and sum(state["opened"].values()) == 1:
            raise ValueError("La dernière caisse ouverte doit rester disponible.")
        return Intervention(time, kind, rid, opened=opened)
    if kind == "move":
        cid = payload.get("customer_id")
        if type(cid) is not int or not any(cid in q for q in state["queues"].values()):
            raise ValueError("Seuls les clients encore dans une file peuvent être déplacés.")
        if not state["opened"][rid]:
            raise ValueError("Ouvre la caisse de destination avant de déplacer le client.")
        if cid in state["queues"][rid]:
            raise ValueError("Le client attend déjà dans cette file.")
        return Intervention(time, kind, rid, customer_id=cid)
    raise ValueError("Action inconnue.")


def apply_interventions(base: DynamicOptions, actions: list[Intervention]) -> DynamicOptions:
    return replace(
        base,
        manual_actions=base.manual_actions
        + tuple((a.time, a.kind, a.register_id, a.customer_id, a.opened) for a in actions),
    )
