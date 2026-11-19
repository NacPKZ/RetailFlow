"""Tests A01 à A06, A11 et A12 du contrat analytique dynamique."""

from inspect import signature

from queuesmart.analytics.dynamic_kpi import DynamicKPICalculator
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import (
    DynamicCustomerResult,
    DynamicEvent,
    DynamicOptions,
    DynamicResult,
    DynamicSimulationEngine,
)


def make_result(customers, events, open_registers=1):
    config = ScenarioConfig("Test KPI", len(customers), 20.0, 2.0, open_registers, seed=42)
    return DynamicResult(config, DynamicOptions(), tuple(events), tuple(customers))


def test_a01_no_customer_is_served_returns_unavailable_wait_kpis():
    customers = [
        DynamicCustomerResult(1, 0.0, 1.0, 1, None, None, 2.0),
        DynamicCustomerResult(2, 0.5, 1.0, 1, None, None, 2.5),
    ]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.5, "customer_arrived", 2),
        DynamicEvent(0.5, "queue_joined", 2, 1, queue_position=2),
        DynamicEvent(2.0, "customer_abandoned", 1, 1),
        DynamicEvent(2.5, "customer_abandoned", 2, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))

    assert report.served_count == 0
    assert report.mean_wait_served_min is None
    assert report.median_wait_served_min is None
    assert report.p90_wait_served_min is None
    assert report.p95_wait_served_min is None
    assert report.mean_service_duration_served_min is None
    assert report.abandonment_rate == 1.0


def test_a02_waits_2_4_6_have_mean_and_median_equal_to_4():
    customers = [
        DynamicCustomerResult(1, 0.0, 1.0, 1, 2.0, 3.0, None),
        DynamicCustomerResult(2, 0.0, 1.0, 1, 4.0, 5.0, None),
        DynamicCustomerResult(3, 0.0, 1.0, 1, 6.0, 7.0, None),
    ]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "customer_arrived", 2),
        DynamicEvent(0.0, "queue_joined", 2, 1, queue_position=2),
        DynamicEvent(0.0, "customer_arrived", 3),
        DynamicEvent(0.0, "queue_joined", 3, 1, queue_position=3),
        DynamicEvent(2.0, "service_started", 1, 1),
        DynamicEvent(3.0, "customer_departed", 1, 1),
        DynamicEvent(4.0, "service_started", 2, 1),
        DynamicEvent(5.0, "customer_departed", 2, 1),
        DynamicEvent(6.0, "service_started", 3, 1),
        DynamicEvent(7.0, "customer_departed", 3, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))

    assert report.mean_wait_served_min == 4.0
    assert report.median_wait_served_min == 4.0
    assert report.p90_wait_served_min == 5.6
    assert report.p95_wait_served_min == 5.8
    assert report.max_wait_served_min == 6.0


def test_a03_partially_open_register_uses_only_its_available_period():
    customers = [
        DynamicCustomerResult(1, 0.0, 4.0, 1, 0.0, 4.0, None),
        DynamicCustomerResult(2, 5.0, 2.0, 2, 6.0, 8.0, None),
    ]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "service_started", 1, 1),
        DynamicEvent(4.0, "customer_departed", 1, 1),
        DynamicEvent(5.0, "register_opened", register_id=2),
        DynamicEvent(5.0, "customer_arrived", 2),
        DynamicEvent(5.0, "queue_joined", 2, 2, queue_position=1),
        DynamicEvent(6.0, "service_started", 2, 2),
        DynamicEvent(8.0, "customer_departed", 2, 2),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))
    register_two = report.registers[1]

    assert register_two.open_time_min == 3.0
    assert register_two.available_time_min == 3.0
    assert register_two.total_service_time_min == 2.0
    assert register_two.utilization_rate == 2.0 / 3.0


def test_a04_abandonment_wait_is_not_mixed_with_served_wait():
    customers = [
        DynamicCustomerResult(1, 0.0, 1.0, 1, 1.0, 2.0, None),
        DynamicCustomerResult(2, 0.0, 1.0, 1, None, None, 3.0),
    ]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "customer_arrived", 2),
        DynamicEvent(0.0, "queue_joined", 2, 1, queue_position=2),
        DynamicEvent(1.0, "service_started", 1, 1),
        DynamicEvent(2.0, "customer_departed", 1, 1),
        DynamicEvent(3.0, "customer_abandoned", 2, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))

    assert report.mean_wait_served_min == 1.0
    assert report.mean_time_before_abandonment_min == 3.0
    assert report.served_waits_min == (1.0,)
    assert report.abandoned_waits_min == (3.0,)
    assert report.abandonment_rate == 0.5


def test_a05_flow_conservation_at_an_intermediate_time_includes_waiting_and_service():
    customers = [
        DynamicCustomerResult(1, 0.0, 2.0, 1, 0.0, 2.0, None),
        DynamicCustomerResult(2, 1.0, 1.0, 1, 2.0, 3.0, None),
    ]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "service_started", 1, 1),
        DynamicEvent(1.0, "customer_arrived", 2),
        DynamicEvent(1.0, "queue_joined", 2, 1, queue_position=1),
        DynamicEvent(2.0, "customer_departed", 1, 1),
        DynamicEvent(2.0, "service_started", 2, 1),
        DynamicEvent(3.0, "customer_departed", 2, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))
    point = next(point for point in report.flow_timeline if point.time_min == 1.0)

    assert point.arrived_count == 2
    assert point.completed_count == 0
    assert point.waiting_count == 1
    assert point.in_service_count == 1
    assert point.present_count == 2
    assert point.is_conserved is True


def test_a06_playback_speed_does_not_change_analytics():
    config = ScenarioConfig("Démo", 30, 30.0, 2.0, 2, seed=42)
    result = DynamicSimulationEngine().run(config)
    calculator = DynamicKPICalculator()
    parameters = tuple(signature(calculator.compute).parameters)
    report = calculator.compute(result)

    # Le calcul analytique reçoit uniquement le résultat métier, jamais une vitesse d'animation.
    assert parameters == ("result",)
    assert calculator.compute(result) == report


def test_a11_all_customers_abandon_mean_wait_of_served_is_unavailable():
    customers = [
        DynamicCustomerResult(1, 0.0, 2.0, 1, None, None, 1.0),
        DynamicCustomerResult(2, 0.0, 2.0, 1, None, None, 1.5),
    ]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "customer_arrived", 2),
        DynamicEvent(0.0, "queue_joined", 2, 1, queue_position=2),
        DynamicEvent(1.0, "customer_abandoned", 1, 1),
        DynamicEvent(1.5, "customer_abandoned", 2, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))

    assert report.served_count == 0
    assert report.abandoned_count == 2
    assert report.mean_wait_served_min is None
    assert report.abandonment_rate == 1.0
    assert report.mean_time_before_abandonment_min == 1.25


def test_a12_simultaneous_events_keep_the_original_event_order():
    customers = [DynamicCustomerResult(1, 0.0, 1.0, 1, 0.0, 1.0, None)]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "service_started", 1, 1),
        DynamicEvent(1.0, "customer_departed", 1, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))
    at_zero = next(
        point
        for point in report.queue_timeline
        if point.time_min == 0.0 and point.register_id == 1
    )

    assert at_zero.waiting_count == 0
    assert at_zero.in_service_count == 1
    assert report.flow_timeline[0].is_conserved is True


def test_service_in_progress_continues_in_effective_availability_after_closure():
    customers = [DynamicCustomerResult(1, 0.0, 3.0, 1, 0.0, 3.0, None)]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.0, "service_started", 1, 1),
        DynamicEvent(1.0, "register_closed", register_id=1),
        DynamicEvent(3.0, "customer_departed", 1, 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events, open_registers=2))
    register_one = report.registers[0]

    assert register_one.open_time_min == 1.0
    assert register_one.total_service_time_min == 3.0
    assert register_one.available_time_min == 3.0
    assert register_one.utilization_rate == 1.0


def test_optional_register_fields_use_the_customer_assignment_when_available():
    customers = [DynamicCustomerResult(1, 0.0, 1.0, 1, 0.0, 1.0, None)]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1),
        DynamicEvent(0.0, "service_started", 1),
        DynamicEvent(1.0, "customer_departed", 1),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events))
    at_zero = next(
        point
        for point in report.queue_timeline
        if point.time_min == 0.0 and point.register_id == 1
    )

    assert at_zero.waiting_count == 0
    assert at_zero.in_service_count == 1
    assert report.flow_timeline[-1].is_conserved is True


def test_queue_switch_updates_source_and_target_register_states():
    customers = [DynamicCustomerResult(1, 0.0, 2.0, 2, 1.0, 3.0, None)]
    events = [
        DynamicEvent(0.0, "customer_arrived", 1),
        DynamicEvent(0.0, "queue_joined", 1, 1, queue_position=1),
        DynamicEvent(0.5, "queue_switched", 1, 1, 2, queue_position=1),
        DynamicEvent(1.0, "service_started", 1, 2),
        DynamicEvent(3.0, "customer_departed", 1, 2),
    ]

    report = DynamicKPICalculator().compute(make_result(customers, events, open_registers=2))
    source_at_switch = next(
        point for point in report.queue_timeline
        if point.time_min == 0.5 and point.register_id == 1
    )
    target_at_switch = next(
        point for point in report.queue_timeline
        if point.time_min == 0.5 and point.register_id == 2
    )

    assert source_at_switch.waiting_count == 0
    assert target_at_switch.waiting_count == 1
    assert all(point.is_conserved for point in report.flow_timeline)
