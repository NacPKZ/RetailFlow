"""Contrat d'événements pour la visualisation 2D de simulations FIFO fixes.

Ce module convertit un résultat existant en événements horodatés sans modifier
le moteur. Les abandons, changements de file et caisses dynamiques ne sont PAS
pris en charge par le moteur actuel et ne sont donc pas inventés ici.
"""

from dataclasses import asdict, dataclass
from typing import Literal

from queuesmart.simulation.result import SimulationResult

EventType = Literal["customer_arrived", "queue_joined", "service_started", "customer_departed"]


@dataclass(frozen=True)
class SimulationEvent:
    time: float
    type: EventType
    customer_id: int
    register_id: int
    queue_position: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_EVENT_PRIORITY = {
    "customer_departed": 0,
    "service_started": 1,
    "customer_arrived": 2,
    "queue_joined": 3,
}


def events_from_result(result: SimulationResult) -> tuple[SimulationEvent, ...]:
    """Expose les faits calculés par le moteur, dans un ordre stable.

    queue_position est le rang dans la file juste après l'arrivée (1 = tête),
    service en cours exclu. Le calcul repose sur les intervalles de service
    des clients déjà affectés à la même caisse.
    """
    events: list[SimulationEvent] = []
    for customer in result.customers:
        if customer.register_id is None or customer.service_start is None:
            raise ValueError("Résultat incomplet : client sans affectation ou début de service")
        previous = [
            other for other in result.customers
            if other.register_id == customer.register_id
            and other.customer_id != customer.customer_id
            and other.arrival_time <= customer.arrival_time
            and other.service_start >= customer.arrival_time
            and (other.arrival_time, other.customer_id)
            < (customer.arrival_time, customer.customer_id)
        ]
        events.extend((
            SimulationEvent(customer.arrival_time, "customer_arrived", customer.customer_id, customer.register_id),
            SimulationEvent(customer.arrival_time, "queue_joined", customer.customer_id, customer.register_id, len(previous) + 1),
            SimulationEvent(customer.service_start, "service_started", customer.customer_id, customer.register_id),
            SimulationEvent(customer.service_end, "customer_departed", customer.customer_id, customer.register_id),
        ))
    return tuple(sorted(events, key=lambda e: (e.time, _EVENT_PRIORITY[e.type], e.customer_id)))
