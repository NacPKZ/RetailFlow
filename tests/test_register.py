"""Tests de la caisse, sur des cas calculés à la main.

Scénario de référence (une caisse) :
    client 1 : arrive à 0, dure 4  -> servi de 0 à 4
    client 2 : arrive à 1, dure 2  -> servi de 4 à 6 (attend 3)
    client 3 : arrive à 10, dure 1 -> servi de 10 à 11 (caisse libre, attend 0)
"""

import pytest

from queuesmart.domain.customer import Customer
from queuesmart.domain.register import CheckoutRegister


@pytest.fixture
def register() -> CheckoutRegister:
    register = CheckoutRegister(register_id=1)
    for customer in (Customer(1, 0.0, 4.0), Customer(2, 1.0, 2.0), Customer(3, 10.0, 1.0)):
        register.serve(customer)
    return register


def test_empty_register() -> None:
    register = CheckoutRegister(3)
    assert register.register_id == 3
    assert register.customers == ()
    assert register.busy_until == 0.0
    assert register.queue_length_at(5.0) == 0
    assert register.estimated_wait_at(5.0) == 0.0
    assert register.busy_time() == 0.0


def test_serve_starts_when_register_is_free(register: CheckoutRegister) -> None:
    starts = [customer.service_start for customer in register.customers]
    assert starts == [0.0, 4.0, 10.0]
    assert register.busy_until == 11.0


def test_customers_are_exposed_read_only(register: CheckoutRegister) -> None:
    assert isinstance(register.customers, tuple)


@pytest.mark.parametrize(("time", "expected"), [(0.5, 1), (2.0, 2), (5.0, 1), (7.0, 0), (10.5, 1)])
def test_queue_length_counts_present_customers(
    register: CheckoutRegister, time: float, expected: int
) -> None:
    assert register.queue_length_at(time) == expected


@pytest.mark.parametrize(
    ("time", "expected"), [(0.5, 3.5), (2.0, 4.0), (5.0, 1.0), (7.0, 0.0), (10.5, 0.5)]
)
def test_estimated_wait_ignores_future_arrivals(
    register: CheckoutRegister, time: float, expected: float
) -> None:
    assert register.estimated_wait_at(time) == pytest.approx(expected)


def test_busy_time_is_sum_of_services(register: CheckoutRegister) -> None:
    assert register.busy_time() == 7.0
