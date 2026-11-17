"""Moteur de simulation : orchestre générateur, stratégie et caisses."""

from queuesmart.config import ScenarioConfig
from queuesmart.domain.register import CheckoutRegister
from queuesmart.simulation.generator import CustomerGenerator
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import AssignmentStrategy


class SimulationEngine:
    """Fait passer les clients d'un scénario aux caisses, dans l'ordre d'arrivée.

    Le moteur ne sait pas *comment* un client choisit sa caisse : il délègue
    à la stratégie reçue (composition + polymorphisme).
    """

    def __init__(self, strategy: AssignmentStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> AssignmentStrategy:
        return self._strategy

    def run(self, config: ScenarioConfig) -> SimulationResult:
        """Simule un scénario complet et renvoie un résultat immuable."""
        customers = CustomerGenerator(config).generate()
        registers = [
            CheckoutRegister(register_id) for register_id in range(1, config.open_registers + 1)
        ]
        for customer in customers:
            chosen = self._strategy.choose(registers, customer.arrival_time)
            chosen.serve(customer)
        return SimulationResult(config, self._strategy.name, tuple(customers), tuple(registers))
