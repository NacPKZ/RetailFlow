"""Tests du client."""

import pytest

from queuesmart.domain.customer import Customer
from queuesmart.exceptions import CustomerNotServedError, InvalidAssignmentError


@pytest.fixture
def customer() -> Customer:
    return Customer(customer_id=1, arrival_time=10.0, service_duration=3.0)


def test_new_customer_is_not_served(customer: Customer) -> None:
    assert not customer.is_served


def test_assign_sets_register_and_times(customer: Customer) -> None:
    customer.assign(register_id=2, service_start=12.0)
    assert customer.is_served
    assert customer.register_id == 2
    assert customer.service_end == 15.0
    assert customer.wait_time == 2.0


def test_cannot_be_assigned_twice(customer: Customer) -> None:
    customer.assign(1, 10.0)
    with pytest.raises(InvalidAssignmentError):
        customer.assign(2, 11.0)


def test_cannot_be_served_before_arrival(customer: Customer) -> None:
    with pytest.raises(InvalidAssignmentError):
        customer.assign(1, 9.0)


@pytest.mark.parametrize("attribute", ["service_end", "wait_time"])
def test_times_unknown_before_assignment(customer: Customer, attribute: str) -> None:
    with pytest.raises(CustomerNotServedError):
        getattr(customer, attribute)


@pytest.mark.parametrize(
    ("time", "waiting", "serving"),
    [(9.9, False, False), (10.0, True, False), (11.9, True, False),
     (12.0, False, True), (14.9, False, True), (15.0, False, False)],
)
def test_state_over_time(customer: Customer, time: float, waiting: bool, serving: bool) -> None:
    customer.assign(1, 12.0)
    assert customer.is_waiting_at(time) is waiting
    assert customer.is_being_served_at(time) is serving
    assert customer.is_present_at(time) is (waiting or serving)


def test_unassigned_customer_waits_after_arrival(customer: Customer) -> None:
    assert customer.is_waiting_at(20.0)
    assert not customer.is_being_served_at(20.0)
