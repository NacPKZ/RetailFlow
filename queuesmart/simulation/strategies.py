"""Comportements des clients pour choisir une caisse (patron Stratégie).

Ajouter un comportement = écrire une sous-classe et l'ajouter au registre
``STRATEGIES`` ; le moteur et l'interface n'ont pas à changer (aucun ``if/elif``).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import ClassVar

from queuesmart.domain.register import CheckoutRegister
from queuesmart.exceptions import UnknownStrategyError


class AssignmentStrategy(ABC):
    """Règle de choix d'une caisse par un client qui arrive."""

    name: ClassVar[str]  # identifiant technique
    label: ClassVar[str]  # libellé affiché dans l'interface

    @abstractmethod
    def choose(self, registers: Sequence[CheckoutRegister], time: float) -> CheckoutRegister:
        """Caisse choisie par un client arrivant à l'instant ``time``."""


class ShortestQueueStrategy(AssignmentStrategy):
    """Comportement réel : le client compte les personnes et prend la file la plus courte."""

    name = "shortest_queue"
    label = "File la plus courte"

    def choose(self, registers: Sequence[CheckoutRegister], time: float) -> CheckoutRegister:
        return _lowest(registers, lambda register: register.queue_length_at(time))


class LeastWaitStrategy(AssignmentStrategy):
    """Avec écran client : le client suit l'attente estimée la plus faible."""

    name = "least_wait"
    label = "Attente estimée minimale (écran client)"

    def choose(self, registers: Sequence[CheckoutRegister], time: float) -> CheckoutRegister:
        return _lowest(registers, lambda register: register.estimated_wait_at(time))


def _lowest(
    registers: Sequence[CheckoutRegister], cost: Callable[[CheckoutRegister], float]
) -> CheckoutRegister:
    """Caisse de coût minimal ; en cas d'égalité, la plus petite (choix déterministe)."""
    if not registers:
        raise ValueError("Aucune caisse ouverte : impossible de choisir.")
    return min(registers, key=lambda register: (cost(register), register.register_id))


STRATEGIES: dict[str, type[AssignmentStrategy]] = {
    strategy.name: strategy for strategy in (ShortestQueueStrategy, LeastWaitStrategy)
}


def build_strategy(name: str) -> AssignmentStrategy:
    """Instancie un comportement à partir de son nom (registre, pas de ``if/elif``)."""
    try:
        return STRATEGIES[name]()
    except KeyError:
        known = ", ".join(STRATEGIES)
        raise UnknownStrategyError(
            f"Comportement client inconnu : « {name} ». Valeurs possibles : {known}."
        ) from None
