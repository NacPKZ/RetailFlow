"""Construction de résultats de simulation « à la main », aux valeurs connues."""

from collections.abc import Sequence

from queuesmart.config import ScenarioConfig
from queuesmart.domain.customer import Customer
from queuesmart.domain.register import CheckoutRegister
from queuesmart.simulation.result import SimulationResult


def build_result(
    assignments: Sequence[tuple[float, float, int]], register_count: int
) -> SimulationResult:
    """Construit un résultat déterministe, sans tirage aléatoire.

    ``assignments`` : (arrivée, durée de service, numéro de caisse) par client,
    dans l'ordre d'arrivée. Les identifiants clients commencent à 1.
    """
    registers = [CheckoutRegister(register_id) for register_id in range(1, register_count + 1)]
    customers = []
    for customer_id, (arrival, duration, register_id) in enumerate(assignments, start=1):
        customer = Customer(customer_id, arrival, duration)
        registers[register_id - 1].serve(customer)
        customers.append(customer)
    config = ScenarioConfig("Manuel", len(customers), 60.0, 2.0, register_count)
    return SimulationResult(config, "manuel", tuple(customers), tuple(registers))
