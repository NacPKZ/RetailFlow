"""KPI et reconstruction des états pour le moteur événementiel dynamique.

Tous les temps sont exprimés en minutes simulées. Les attentes des clients
servis et les temps passés avant abandon sont calculés séparément.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from queuesmart.simulation.dynamic import DynamicResult

REGISTER_IDS = range(1, 6)


@dataclass(frozen=True)
class DynamicQueuePoint:
    """État d'une caisse après le traitement de tous les événements à cet instant."""

    time_min: float
    register_id: int
    waiting_count: int
    in_service_count: int
    is_open: bool
    estimated_wait_last_customer_min: float


@dataclass(frozen=True)
class DynamicFlowPoint:
    """Conservation des clients à un instant, après les événements simultanés."""

    time_min: float
    arrived_count: int
    completed_count: int
    abandoned_count: int
    waiting_count: int
    in_service_count: int
    present_count: int
    is_conserved: bool


@dataclass(frozen=True)
class DynamicRegisterKPI:
    """Indicateurs d'une caisse sur la fenêtre observée."""

    register_id: int
    served_count: int
    mean_wait_served_min: float | None
    total_service_time_min: float
    open_time_min: float
    available_time_min: float
    utilization_rate: float | None
    peak_queue_length: int


@dataclass(frozen=True)
class DynamicKPIReport:
    """Rapport analytique calculé exclusivement depuis un ``DynamicResult``.

    Les quantiles utilisent l'interpolation linéaire inclusive (méthode
    ``statistics.quantiles(..., method="inclusive")``). Les attentes avant
    abandon sont conservées dans une population distincte.
    """

    arrival_count: int
    served_count: int
    abandoned_count: int
    mean_wait_served_min: float | None
    median_wait_served_min: float | None
    p90_wait_served_min: float | None
    p95_wait_served_min: float | None
    max_wait_served_min: float | None
    mean_service_duration_served_min: float | None
    mean_total_time_served_min: float | None
    total_time_served_customer_min: float | None
    abandonment_rate: float | None
    mean_time_before_abandonment_min: float | None
    throughput_served_per_min: float | None
    observation_start_min: float | None
    observation_end_min: float | None
    served_waits_min: tuple[float, ...]
    abandoned_waits_min: tuple[float, ...]
    queue_timeline: tuple[DynamicQueuePoint, ...]
    flow_timeline: tuple[DynamicFlowPoint, ...]
    registers: tuple[DynamicRegisterKPI, ...]
    customer_rows: tuple[dict[str, object], ...]


class DynamicKPICalculator:
    """Calcule les KPI d'un résultat dynamique sans utiliser le calculateur FIFO."""

    def compute(self, result: DynamicResult) -> DynamicKPIReport:
        served = [
            customer
            for customer in result.customers
            if customer.service_start is not None and customer.departure_time is not None
        ]
        abandoned = [customer for customer in result.customers if customer.abandoned_at is not None]

        served_waits = tuple(
            customer.service_start - customer.arrival_time
            for customer in served
            if customer.service_start is not None
        )
        abandoned_waits = tuple(
            customer.abandoned_at - customer.arrival_time
            for customer in abandoned
            if customer.abandoned_at is not None
        )
        service_durations = tuple(customer.service_duration for customer in served)
        total_times_served = tuple(
            customer.departure_time - customer.arrival_time
            for customer in served
            if customer.departure_time is not None
        )

        observation_start = min(
            (customer.arrival_time for customer in result.customers), default=None
        )
        terminal_times = [
            customer.departure_time
            for customer in result.customers
            if customer.departure_time is not None
        ] + [
            customer.abandoned_at
            for customer in result.customers
            if customer.abandoned_at is not None
        ]
        observation_end = max(terminal_times, default=None)
        observation_duration = (
            observation_end - observation_start
            if observation_start is not None and observation_end is not None
            else None
        )

        queue_timeline, flow_timeline, peak_queues = _reconstruct_event_states(result)
        register_kpis = _compute_register_kpis(result, served, queue_timeline, observation_end)

        return DynamicKPIReport(
            arrival_count=len(result.customers),
            served_count=len(served),
            abandoned_count=len(abandoned),
            mean_wait_served_min=_mean(served_waits),
            median_wait_served_min=statistics.median(served_waits) if served_waits else None,
            p90_wait_served_min=_percentile(served_waits, 0.90),
            p95_wait_served_min=_percentile(served_waits, 0.95),
            max_wait_served_min=max(served_waits) if served_waits else None,
            mean_service_duration_served_min=_mean(service_durations),
            mean_total_time_served_min=_mean(total_times_served),
            total_time_served_customer_min=(
                sum(total_times_served) if total_times_served else None
            ),
            abandonment_rate=(len(abandoned) / len(result.customers)) if result.customers else None,
            mean_time_before_abandonment_min=_mean(abandoned_waits),
            throughput_served_per_min=(
                len(served) / observation_duration
                if observation_duration is not None and observation_duration > 0
                else None
            ),
            observation_start_min=observation_start,
            observation_end_min=observation_end,
            served_waits_min=served_waits,
            abandoned_waits_min=abandoned_waits,
            queue_timeline=tuple(queue_timeline),
            flow_timeline=tuple(flow_timeline),
            registers=tuple(register_kpis),
            customer_rows=tuple(_customer_rows(result)),
        )


def _mean(values: tuple[float, ...]) -> float | None:
    return statistics.fmean(values) if values else None


def _percentile(values: tuple[float, ...], probability: float) -> float | None:
    """Quantile linéaire inclusive, identique à la convention NumPy ``linear``."""
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    quantiles = statistics.quantiles(values, n=100, method="inclusive")
    index = round(probability * 100) - 1
    return quantiles[index]


def _customer_rows(result: DynamicResult) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for customer in result.customers:
        is_served = customer.service_start is not None and customer.departure_time is not None
        is_abandoned = customer.abandoned_at is not None
        served_wait = (
            customer.service_start - customer.arrival_time
            if is_served and customer.service_start is not None
            else None
        )
        abandoned_wait = (
            customer.abandoned_at - customer.arrival_time
            if is_abandoned and customer.abandoned_at is not None
            else None
        )
        terminal_time = customer.departure_time if is_served else customer.abandoned_at
        rows.append(
            {
                "customer_id": customer.customer_id,
                "arrival_time_min": customer.arrival_time,
                "register_id": customer.register_id,
                "service_duration_min": customer.service_duration,
                "service_start_min": customer.service_start,
                "departure_time_min": customer.departure_time,
                "abandoned_at_min": customer.abandoned_at,
                "outcome": "servi" if is_served else "abandonné" if is_abandoned else "présent",
                "wait_served_min": served_wait,
                "time_before_abandonment_min": abandoned_wait,
                "total_time_in_system_min": (
                    terminal_time - customer.arrival_time if terminal_time is not None else None
                ),
            }
        )
    return rows


def _reconstruct_event_states(
    result: DynamicResult,
) -> tuple[list[DynamicQueuePoint], list[DynamicFlowPoint], dict[int, int]]:
    """Rejoue les événements sans réordonner les événements de même minute.

    La photographie à t est prise après le dernier événement de l'instant t.
    La longueur de file exclut le client en service.
    """
    queues: dict[int, list[int]] = {register_id: [] for register_id in REGISTER_IDS}
    serving: dict[int, int | None] = {register_id: None for register_id in REGISTER_IDS}
    register_open: dict[int, bool] = {
        register_id: register_id <= result.config.open_registers
        for register_id in REGISTER_IDS
    }
    customer_by_id = {customer.customer_id: customer for customer in result.customers}
    arrived_ids: set[int] = set()
    completed_ids: set[int] = set()
    abandoned_ids: set[int] = set()
    queue_points: list[DynamicQueuePoint] = []
    flow_points: list[DynamicFlowPoint] = []
    peak_queues = {register_id: 0 for register_id in REGISTER_IDS}

    def remove_from_queues(customer_id: int, preferred_register: int | None = None) -> None:
        register_ids = (
            [preferred_register]
            if preferred_register in queues
            else list(REGISTER_IDS)
        )
        for register_id in register_ids:
            if customer_id in queues[register_id]:
                queues[register_id].remove(customer_id)
                return

    def snapshot(time_min: float) -> None:
        waiting_total = sum(len(queue) for queue in queues.values())
        service_total = sum(customer_id is not None for customer_id in serving.values())
        present_total = waiting_total + service_total
        flow = DynamicFlowPoint(
            time_min=time_min,
            arrived_count=len(arrived_ids),
            completed_count=len(completed_ids),
            abandoned_count=len(abandoned_ids),
            waiting_count=waiting_total,
            in_service_count=service_total,
            present_count=present_total,
            is_conserved=(
                len(arrived_ids)
                == len(completed_ids) + len(abandoned_ids) + present_total
            ),
        )
        flow_points.append(flow)

        for register_id in REGISTER_IDS:
            queue = queues[register_id]
            peak_queues[register_id] = max(peak_queues[register_id], len(queue))
            serving_id = serving[register_id]
            remaining_service = 0.0
            if serving_id is not None:
                customer = customer_by_id[serving_id]
                if customer.service_start is not None:
                    remaining_service = max(
                        0.0,
                        customer.service_start + customer.service_duration - time_min,
                    )
            customers_ahead = queue[:-1] if queue else []
            estimated_wait = remaining_service + sum(
                customer_by_id[customer_id].service_duration
                for customer_id in customers_ahead
            )
            queue_points.append(
                DynamicQueuePoint(
                    time_min=time_min,
                    register_id=register_id,
                    waiting_count=len(queue),
                    in_service_count=1 if serving_id is not None else 0,
                    is_open=register_open[register_id],
                    estimated_wait_last_customer_min=estimated_wait,
                )
            )

    events = result.events
    previous_time: float | None = None
    if events and events[0].time > 0:
        snapshot(0.0)

    for event in events:
        if previous_time is not None and event.time < previous_time:
            raise ValueError(
                "Les événements dynamiques doivent être ordonnés par temps croissant."
            )
        if previous_time is not None and event.time != previous_time:
            snapshot(previous_time)
        previous_time = event.time

        customer_id = event.customer_id
        register_id = event.register_id

        if event.type == "customer_arrived" and customer_id is not None:
            arrived_ids.add(customer_id)
        elif event.type == "queue_joined" and customer_id is not None:
            resolved_register = register_id
            if resolved_register not in queues:
                resolved_register = customer_by_id[customer_id].register_id
            if resolved_register in queues and customer_id not in queues[resolved_register]:
                queues[resolved_register].append(customer_id)
        elif event.type == "service_started" and customer_id is not None:
            resolved_register = register_id
            if resolved_register not in queues:
                resolved_register = customer_by_id[customer_id].register_id
            remove_from_queues(customer_id, register_id)
            if resolved_register in queues:
                serving[resolved_register] = customer_id
        elif event.type == "customer_departed" and customer_id is not None:
            if register_id in serving and serving[register_id] == customer_id:
                serving[register_id] = None
            else:
                for current_register, serving_id in serving.items():
                    if serving_id == customer_id:
                        serving[current_register] = None
                        break
            completed_ids.add(customer_id)
        elif event.type == "queue_switched" and customer_id is not None:
            remove_from_queues(customer_id, register_id)
            target_id = event.target_register_id
            if target_id not in queues:
                target_id = customer_by_id[customer_id].register_id
            if target_id in queues and customer_id not in queues[target_id]:
                queues[target_id].append(customer_id)
        elif event.type == "customer_abandoned" and customer_id is not None:
            remove_from_queues(customer_id, register_id)
            abandoned_ids.add(customer_id)
        elif event.type == "register_opened" and register_id in register_open:
            register_open[register_id] = True
        elif event.type == "register_closed" and register_id in register_open:
            register_open[register_id] = False

    if previous_time is not None:
        snapshot(previous_time)
    elif not events:
        snapshot(0.0)

    return queue_points, flow_points, peak_queues


def _compute_register_kpis(
    result: DynamicResult,
    served_customers: list,
    queue_timeline: list[DynamicQueuePoint],
    observation_end: float | None,
) -> list[DynamicRegisterKPI]:
    service_by_register: dict[int, list] = {register_id: [] for register_id in REGISTER_IDS}
    for customer in served_customers:
        if customer.register_id in service_by_register:
            service_by_register[customer.register_id].append(customer)

    open_intervals = _register_open_intervals(result, observation_end)
    queue_peaks = {
        register_id: max(
            (
                point.waiting_count
                for point in queue_timeline
                if point.register_id == register_id
            ),
            default=0,
        )
        for register_id in REGISTER_IDS
    }

    reports: list[DynamicRegisterKPI] = []
    for register_id in REGISTER_IDS:
        customers = service_by_register[register_id]
        service_intervals = [
            (customer.service_start, customer.departure_time)
            for customer in customers
            if customer.service_start is not None and customer.departure_time is not None
        ]
        busy_time = sum(end - start for start, end in service_intervals)
        opened_time = _interval_duration(open_intervals[register_id])
        effective_intervals = _merge_intervals(
            open_intervals[register_id] + service_intervals
        )
        available_time = _interval_duration(effective_intervals)
        reports.append(
            DynamicRegisterKPI(
                register_id=register_id,
                served_count=len(customers),
                mean_wait_served_min=_mean(
                    tuple(
                        customer.service_start - customer.arrival_time
                        for customer in customers
                        if customer.service_start is not None
                    )
                ),
                total_service_time_min=busy_time,
                open_time_min=opened_time,
                available_time_min=available_time,
                utilization_rate=(busy_time / available_time) if available_time > 0 else None,
                peak_queue_length=queue_peaks[register_id],
            )
        )
    return reports


def _register_open_intervals(
    result: DynamicResult, observation_end: float | None
) -> dict[int, list[tuple[float, float]]]:
    intervals = {register_id: [] for register_id in REGISTER_IDS}
    if observation_end is None:
        return intervals

    opened_at: dict[int, float | None] = {
        register_id: 0.0 if register_id <= result.config.open_registers else None
        for register_id in REGISTER_IDS
    }
    for event in result.events:
        if event.time > observation_end:
            break
        register_id = event.register_id
        if register_id not in intervals:
            continue
        if event.type == "register_opened" and opened_at[register_id] is None:
            opened_at[register_id] = event.time
        elif event.type == "register_closed" and opened_at[register_id] is not None:
            start = opened_at[register_id]
            if start is not None and event.time >= start:
                intervals[register_id].append((start, event.time))
            opened_at[register_id] = None

    for register_id, start in opened_at.items():
        if start is not None and observation_end >= start:
            intervals[register_id].append((start, observation_end))
    return intervals


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged: list[tuple[float, float]] = [ordered[0]]
    for start, end in ordered[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged


def _interval_duration(intervals: list[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in intervals)
