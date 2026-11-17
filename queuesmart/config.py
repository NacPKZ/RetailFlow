"""Constantes du projet et configuration validée d'un scénario.

Toutes les valeurs « métier » sont ici : aucun nombre magique ailleurs.
"""

from dataclasses import dataclass, replace

from queuesmart.exceptions import InvalidScenarioError

# --- Caisses -----------------------------------------------------------------
MIN_REGISTERS = 1
MAX_REGISTERS = 8

# --- Durées de passage en caisse (minutes) -----------------------------------
MIN_SERVICE_TIME_MIN = 0.3  # plancher : même un client pressé prend ~20 s
SERVICE_TIME_SHAPE = 2.0  # forme de la loi gamma (dispersion modérée)

# --- Reproductibilité et statistiques -----------------------------------------
DEFAULT_SEED = 42
DEFAULT_REPLICATIONS = 20

# --- Qualité de service --------------------------------------------------------
WAIT_THRESHOLD_MIN = 5.0  # au-delà, un client est considéré comme « en attente longue »
MAX_SHARE_OVER_THRESHOLD = 0.10  # cible : au plus 10 % de clients au-delà du seuil

# --- Bornes des saisies de l'interface ----------------------------------------
MAX_CUSTOMER_COUNT = 500
MIN_ARRIVAL_WINDOW_MIN = 5.0
MAX_ARRIVAL_WINDOW_MIN = 240.0
MAX_MEAN_SERVICE_TIME_MIN = 10.0


@dataclass(frozen=True)
class ScenarioConfig:
    """Paramètres d'une simulation. Immuable et validé dès sa création.

    Tous les temps sont en minutes depuis l'ouverture (t = 0).
    """

    name: str
    customer_count: int
    arrival_window_min: float
    mean_service_time_min: float
    open_registers: int
    seed: int | None = DEFAULT_SEED

    def __post_init__(self) -> None:
        for error in self._validation_errors():
            raise InvalidScenarioError(error)

    def _validation_errors(self) -> list[str]:
        """Liste des règles non respectées, avec un message lisible par l'utilisateur."""
        checks = [
            (self.customer_count >= 1, "Le nombre de clients doit être au moins 1."),
            (self.arrival_window_min > 0, "La durée d'arrivée doit être strictement positive."),
            (
                self.mean_service_time_min >= MIN_SERVICE_TIME_MIN,
                f"Le temps moyen de passage doit être d'au moins {MIN_SERVICE_TIME_MIN} min.",
            ),
            (
                MIN_REGISTERS <= self.open_registers <= MAX_REGISTERS,
                f"Le nombre de caisses doit être entre {MIN_REGISTERS} et {MAX_REGISTERS}.",
            ),
        ]
        return [message for is_valid, message in checks if not is_valid]

    @property
    def arrival_rate_per_min(self) -> float:
        """Nombre moyen de clients arrivant par minute."""
        return self.customer_count / self.arrival_window_min

    def with_registers(self, open_registers: int) -> "ScenarioConfig":
        """Copie du scénario avec un autre nombre de caisses (revalidée)."""
        return replace(self, open_registers=open_registers)

    def with_seed(self, seed: int | None) -> "ScenarioConfig":
        """Copie du scénario avec une autre graine aléatoire."""
        return replace(self, seed=seed)


SCENARIOS: dict[str, ScenarioConfig] = {
    scenario.name: scenario
    for scenario in (
        ScenarioConfig("Heures creuses", 50, 60.0, 2.0, 3),
        ScenarioConfig("Heures normales", 90, 60.0, 2.0, 4),
        ScenarioConfig("Heure de pointe", 145, 60.0, 2.0, 5),
    )
}
