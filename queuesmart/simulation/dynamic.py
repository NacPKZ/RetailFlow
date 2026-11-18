"""Moteur dynamique événementiel, indépendant de l'interface Streamlit.

Une caisse fermée termine le client en cours, puis réaffecte ses clients en
attente aux caisses ouvertes. Les événements sont en minutes simulées.
"""

from __future__ import annotations

import heapq
import itertools
import math
import statistics
from dataclasses import asdict, dataclass
from typing import Literal

from queuesmart.config import ScenarioConfig
from queuesmart.simulation.generator import CustomerGenerator

EventKind = Literal[
    "customer_arrived",
    "queue_joined",
    "service_started",
    "customer_departed",
    "queue_switched",
    "customer_abandoned",
    "register_opened",
    "register_closed",
]


@dataclass(frozen=True)
class DynamicOptions:
    patience_min: float | None = 12.0
    switching_enabled: bool = True
    switching_interval_min: float = 1.0
    switching_gain_min: float = 1.0
    register_changes: tuple[tuple[float, int, bool], ...] = ()
    customer_moves: tuple[tuple[float, int, int], ...] = ()
    manual_actions: tuple[tuple[float, str, int, int | None, bool | None], ...] = ()

    def __post_init__(self):
        for time, kind, rid, cid, opened in self.manual_actions:
            if not math.isfinite(time) or time < 0 or not 1 <= rid <= 5:
                raise ValueError("Intervention invalide.")
            if kind not in ("register", "move"):
                raise ValueError("Type d'intervention inconnu.")
            if kind == "register" and type(opened) is not bool:
                raise ValueError("État de caisse invalide.")
            if kind == "move" and (type(cid) is not int or cid < 1):
                raise ValueError("Client invalide.")
        if self.patience_min is not None and self.patience_min <= 0:
            raise ValueError("La patience doit être positive.")
        if self.switching_interval_min <= 0 or self.switching_gain_min < 0:
            raise ValueError("Intervalle de réévaluation ou gain invalide.")
        for t, register, opened in self.register_changes:
            if (
                not math.isfinite(t)
                or t < 0
                or not 1 <= register <= 5
                or not isinstance(opened, bool)
            ):
                raise ValueError("Changement de caisse invalide.")
        for time, customer_id, target in self.customer_moves:
            if not math.isfinite(time) or time < 0 or customer_id < 1 or not 1 <= target <= 5:
                raise ValueError("Déplacement de client invalide.")


@dataclass(frozen=True)
class DynamicEvent:
    time: float
    type: EventKind
    customer_id: int | None = None
    register_id: int | None = None
    target_register_id: int | None = None
    queue_position: int | None = None

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DynamicCustomerResult:
    customer_id: int
    arrival_time: float
    service_duration: float
    register_id: int | None
    service_start: float | None
    departure_time: float | None
    abandoned_at: float | None

    @property
    def wait_time(self):
        if self.service_start is not None:
            return self.service_start - self.arrival_time
        if self.abandoned_at is not None:
            return self.abandoned_at - self.arrival_time
        return None


@dataclass(frozen=True)
class DynamicResult:
    config: ScenarioConfig
    options: DynamicOptions
    events: tuple[DynamicEvent, ...]
    customers: tuple[DynamicCustomerResult, ...]

    @property
    def served_count(self):
        return sum(c.service_start is not None for c in self.customers)

    @property
    def abandoned_count(self):
        return sum(c.abandoned_at is not None for c in self.customers)

    @property
    def mean_wait_served(self):
        waits = [c.wait_time for c in self.customers if c.service_start is not None]
        return statistics.fmean(waits) if waits else None

    def events_as_dicts(self):
        return [e.to_dict() for e in self.events]


class DynamicSimulationEngine:
    """Moteur déterministe à événements discrets avec files FIFO par caisse."""

    def run(self, config: ScenarioConfig, options: DynamicOptions | None = None) -> DynamicResult:
        options = options or DynamicOptions()
        if not 1 <= config.open_registers <= 5:
            raise ValueError("Le moteur dynamique prend en charge 1 à 5 caisses.")
        people = CustomerGenerator(config).generate()
        by_id = {c.customer_id: c for c in people}
        queues = {r: [] for r in range(1, 6)}
        active = {r: r <= config.open_registers for r in range(1, 6)}
        serving = {r: None for r in range(1, 6)}
        ends = {r: 0.0 for r in range(1, 6)}
        service_start = {}
        departure = {}
        abandoned = {}
        assigned = {}
        manually_assigned = set()
        events = []
        agenda = []
        sequence = itertools.count()
        epsilon = 1e-9

        def schedule(time, priority, kind, payload=None):
            heapq.heappush(agenda, (time, priority, next(sequence), kind, payload))

        def emit(time, kind, cid=None, rid=None, target=None, position=None):
            events.append(DynamicEvent(time, kind, cid, rid, target, position))

        def estimated_wait(rid, time):
            remaining = max(0.0, ends[rid] - time) if serving[rid] is not None else 0.0
            return remaining + sum(by_id[c].service_duration for c in queues[rid])

        def best_register(time):
            opened = [r for r in active if active[r]]
            if not opened:
                return None
            return min(opened, key=lambda r: (estimated_wait(r, time), r))

        def start_next(rid, time):
            if serving[rid] is not None or not active[rid] or not queues[rid]:
                return
            cid = queues[rid].pop(0)
            serving[rid] = cid
            service_start[cid] = time
            ends[rid] = time + by_id[cid].service_duration
            emit(time, "service_started", cid, rid)
            schedule(ends[rid], 0, "complete", (rid, cid))

        for person in people:
            schedule(person.arrival_time, 2, "arrival", person.customer_id)
            if options.patience_min is not None:
                schedule(
                    person.arrival_time + options.patience_min, 3, "patience", person.customer_id
                )
        for t, rid, opened in options.register_changes:
            schedule(t, 1, "register", (rid, opened))
        for t, cid, target in options.customer_moves:
            schedule(t, 2.5, "manual_move", (cid, target))
        # Même priorité pour les gestes : leur ordre reste celui de l'utilisateur,
        # même si deux interventions sont faites à la même minute de pause.
        for t, kind, rid, cid, opened in options.manual_actions:
            schedule(
                t,
                2.75,
                "register" if kind == "register" else "manual_move",
                (rid, opened) if kind == "register" else (cid, rid),
            )
        if options.switching_enabled:
            schedule(options.switching_interval_min, 4, "review")

        last_event_time = max((p.arrival_time for p in people), default=0.0)
        while agenda:
            time, _, _, kind, payload = heapq.heappop(agenda)
            last_event_time = max(last_event_time, time)
            if kind == "complete":
                rid, cid = payload
                if serving[rid] != cid:
                    continue
                serving[rid] = None
                departure[cid] = time
                emit(time, "customer_departed", cid, rid)
                start_next(rid, time)
            elif kind == "register":
                rid, opened = payload
                if active[rid] == opened:
                    continue
                if not opened and sum(active.values()) == 1:
                    # Ne jamais laisser le magasin sans caisse ouverte.
                    continue
                active[rid] = opened
                emit(time, "register_opened" if opened else "register_closed", rid=rid)
                if opened:
                    start_next(rid, time)
                else:
                    pending = list(queues[rid])
                    queues[rid].clear()
                    for cid in pending:
                        target = best_register(time)
                        if target is None:
                            raise RuntimeError("Aucune caisse de réaffectation.")
                        assigned[cid] = target
                        queues[target].append(cid)
                        emit(time, "queue_switched", cid, rid, target, len(queues[target]))
                        start_next(target, time)
            elif kind == "arrival":
                cid = payload
                emit(time, "customer_arrived", cid)
                rid = best_register(time)
                if rid is None:
                    raise RuntimeError("Aucune caisse ouverte à l’arrivée.")
                assigned[cid] = rid
                queues[rid].append(cid)
                emit(time, "queue_joined", cid, rid, position=len(queues[rid]))
                start_next(rid, time)
            elif kind == "manual_move":
                cid, target = payload
                source = assigned.get(cid)
                # Les commandes ne déplacent ni un client servi, ni une caisse fermée.
                if source is None or not active[target] or cid not in queues[source]:
                    continue
                if source == target:
                    continue
                queues[source].remove(cid)
                queues[target].append(cid)
                assigned[cid] = target
                manually_assigned.add(cid)
                emit(time, "queue_switched", cid, source, target, len(queues[target]))
                start_next(target, time)
            elif kind == "patience":
                cid = payload
                if cid in service_start or cid in abandoned:
                    continue
                rid = assigned.get(cid)
                if rid is not None and cid in queues[rid]:
                    queues[rid].remove(cid)
                    abandoned[cid] = time
                    emit(time, "customer_abandoned", cid, rid)
            elif kind == "review" and options.switching_enabled:
                # Une revue ne doit pas s'éterniser après la fin des arrivées.
                for rid in range(1, 6):
                    for cid in list(queues[rid]):
                        if cid not in queues[rid] or cid in manually_assigned:
                            continue
                        target = best_register(time)
                        if target is None or target == rid:
                            continue
                        own_wait = max(0.0, ends[rid] - time) if serving[rid] else 0.0
                        own_wait += sum(
                            by_id[c].service_duration for c in queues[rid][: queues[rid].index(cid)]
                        )
                        alternative = estimated_wait(target, time)
                        if own_wait > alternative + options.switching_gain_min + epsilon:
                            queues[rid].remove(cid)
                            queues[target].append(cid)
                            assigned[cid] = target
                            emit(time, "queue_switched", cid, rid, target, len(queues[target]))
                            start_next(target, time)
                if any(
                    c.customer_id not in service_start and c.customer_id not in abandoned
                    for c in people
                ) or any(serving.values()):
                    schedule(time + options.switching_interval_min, 4, "review")
        results = tuple(
            DynamicCustomerResult(
                p.customer_id,
                p.arrival_time,
                p.service_duration,
                assigned.get(p.customer_id),
                service_start.get(p.customer_id),
                departure.get(p.customer_id),
                abandoned.get(p.customer_id),
            )
            for p in people
        )
        if len(results) != len(service_start) + len(abandoned):
            raise RuntimeError("Des clients n’ont pas été traités.")
        return DynamicResult(config, options, tuple(events), results)
