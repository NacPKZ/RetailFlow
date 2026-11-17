"""Résultat d'une simulation et photographies (snapshots) de l'état du magasin."""

import math
from dataclasses import dataclass
from functools import cached_property

from queuesmart.config import ScenarioConfig
from queuesmart.domain.customer import Customer
from queuesmart.domain.register import CheckoutRegister
from queuesmart.exceptions import UnknownCustomerError


@dataclass(frozen=True)
class RegisterSnapshot:
    """État d'une caisse à un instant donné."""

    register_id: int
    serving_customer_id: int | None
    waiting_customer_ids: tuple[int, ...]  # dans l'ordre de la file
    estimated_wait: float

    @property
    def queue_length(self) -> int:
        """Clients présents à la caisse, service compris (même sens que dans le domaine)."""
        return len(self.waiting_customer_ids) + (self.serving_customer_id is not None)


@dataclass(frozen=True)
class StoreSnapshot:
    """État de toutes les caisses à un instant donné."""

    time: float
    registers: tuple[RegisterSnapshot, ...]
    not_arrived_count: int
    departed_count: int


@dataclass(frozen=True)
class SimulationResult:
    """Tout ce qu'a produit une simulation. Les onglets ne lisent que cet objet."""

    config: ScenarioConfig
    strategy_name: str
    customers: tuple[Customer, ...]
    registers: tuple[CheckoutRegister, ...]

    @property
    def end_time(self) -> float:
        """Instant où le dernier client quitte sa caisse."""
        return max(customer.service_end for customer in self.customers)

    def customer(self, customer_id: int) -> Customer:
        """Retrouve un client par son identifiant."""
        try:
            return self._customers_by_id[customer_id]
        except KeyError:
            raise UnknownCustomerError(
                f"Aucun client n°{customer_id} dans cette simulation "
                f"(identifiants de 1 à {len(self.customers)})."
            ) from None

    def snapshot_at(self, time: float) -> StoreSnapshot:
        """Photographie du magasin à l'instant ``time``."""
        return StoreSnapshot(
            time=time,
            registers=tuple(_register_snapshot(register, time) for register in self.registers),
            not_arrived_count=sum(1 for c in self.customers if c.arrival_time > time),
            departed_count=sum(1 for c in self.customers if c.service_end <= time),
        )

    def timeline(self, step_min: float) -> list[StoreSnapshot]:
        """Snapshots réguliers de t = 0 jusqu'à la fin (incluse), tous les ``step_min``."""
        if step_min <= 0:
            raise ValueError("Le pas de temps doit être strictement positif.")
        step_count = math.ceil(self.end_time / step_min)
        times = [min(index * step_min, self.end_time) for index in range(step_count + 1)]
        return [self.snapshot_at(time) for time in times]

    @cached_property
    def _customers_by_id(self) -> dict[int, Customer]:
        return {customer.customer_id: customer for customer in self.customers}


def _register_snapshot(register: CheckoutRegister, time: float) -> RegisterSnapshot:
    serving_ids = [c.customer_id for c in register.customers if c.is_being_served_at(time)]
    return RegisterSnapshot(
        register_id=register.register_id,
        serving_customer_id=serving_ids[0] if serving_ids else None,
        waiting_customer_ids=tuple(
            c.customer_id for c in register.customers if c.is_waiting_at(time)
        ),
        estimated_wait=register.estimated_wait_at(time),
    )
