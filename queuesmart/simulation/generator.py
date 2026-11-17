"""Génération aléatoire (mais reproductible) des clients d'un scénario."""

import random

from queuesmart.config import MIN_SERVICE_TIME_MIN, SERVICE_TIME_SHAPE, ScenarioConfig
from queuesmart.domain.customer import Customer


class CustomerGenerator:
    """Crée les clients d'un scénario : heures d'arrivée et durées de passage.

    - Arrivées : ``customer_count`` instants uniformes sur la fenêtre, triés.
      C'est équivalent à un processus de Poisson conditionné au nombre d'arrivées.
    - Durées : loi gamma de moyenne ``mean_service_time_min``, avec un plancher.
    """

    def __init__(self, config: ScenarioConfig) -> None:
        self._config = config

    def generate(self) -> list[Customer]:
        """Liste des clients, triés par heure d'arrivée, identifiants à partir de 1.

        Un ``random.Random`` dédié est créé à chaque appel (jamais le ``random``
        global) : même graine, mêmes clients, quel que soit le nombre d'appels.
        """
        rng = random.Random(self._config.seed)
        arrivals = self._arrival_times(rng)
        return [
            Customer(customer_id, arrival, self._service_duration(rng))
            for customer_id, arrival in enumerate(arrivals, start=1)
        ]

    def _arrival_times(self, rng: random.Random) -> list[float]:
        window = self._config.arrival_window_min
        return sorted(rng.uniform(0.0, window) for _ in range(self._config.customer_count))

    def _service_duration(self, rng: random.Random) -> float:
        # Loi gamma : moyenne = forme x échelle, donc échelle = moyenne / forme.
        scale = self._config.mean_service_time_min / SERVICE_TIME_SHAPE
        return max(MIN_SERVICE_TIME_MIN, rng.gammavariate(SERVICE_TIME_SHAPE, scale))
