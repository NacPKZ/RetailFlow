"""Géométrie de la vue du dessus du magasin. PUR : aucun import de Streamlit ni Plotly.

Les caisses sont alignées en haut (y = 0) ; chaque file descend verticalement
sous sa caisse. Le client en service est placé sur la caisse elle-même.
"""

from dataclasses import dataclass

from queuesmart.config import WAIT_THRESHOLD_MIN
from queuesmart.domain.customer import Customer
from queuesmart.simulation.result import RegisterSnapshot, SimulationResult, StoreSnapshot
from queuesmart.ui.client_board import format_minutes

ANIMATION_STEP_MIN = 0.5
MAX_FRAMES = 240  # au-delà, on élargit le pas pour garder une animation fluide

WAITING = "waiting"
SERVING = "serving"

REGISTER_SPACING = 2.0  # écart horizontal entre deux caisses
QUEUE_SPACING = 1.0  # écart vertical entre deux clients d'une même file
REGISTER_Y = 0.0

WAIT_OK = "ok"
WAIT_WARNING = "warning"
WAIT_CRITICAL = "critical"
WARNING_SHARE_OF_THRESHOLD = 0.5  # orange dès la moitié du seuil


@dataclass(frozen=True)
class PlacedCustomer:
    """Un client à dessiner, avec sa position et son état."""

    customer_id: int
    x: float
    y: float
    state: str  # WAITING | SERVING
    wait_so_far: float  # minutes déjà attendues à cet instant (pour la couleur)


class StoreLayout:
    """Calcule où dessiner les caisses et les clients."""

    def __init__(self, register_count: int) -> None:
        if register_count < 1:
            raise ValueError("Il faut au moins une caisse à dessiner.")
        self._register_count = register_count

    def register_position(self, register_id: int) -> tuple[float, float]:
        """Coordonnées (x, y) de la caisse ``register_id`` (numérotée à partir de 1)."""
        if not 1 <= register_id <= self._register_count:
            raise ValueError(f"Caisse {register_id} hors plan (1 à {self._register_count}).")
        return (register_id - 1) * REGISTER_SPACING, REGISTER_Y

    def place_customers(
        self, snapshot: StoreSnapshot, result: SimulationResult
    ) -> list[PlacedCustomer]:
        """Position de chaque client présent aux caisses à l'instant du snapshot."""
        placed: list[PlacedCustomer] = []
        for register in snapshot.registers:
            placed.extend(self._place_register(register, snapshot.time, result))
        return placed

    def _place_register(
        self, register: RegisterSnapshot, time: float, result: SimulationResult
    ) -> list[PlacedCustomer]:
        x, y = self.register_position(register.register_id)
        placed = []
        if register.serving_customer_id is not None:
            served = result.customer(register.serving_customer_id)
            placed.append(PlacedCustomer(served.customer_id, x, y, SERVING, served.wait_time))
        for rank, customer_id in enumerate(register.waiting_customer_ids, start=1):
            waited = time - result.customer(customer_id).arrival_time
            placed.append(PlacedCustomer(customer_id, x, y - rank * QUEUE_SPACING, WAITING, waited))
        return placed


def animation_step(end_time: float) -> float:
    """Pas de l'animation : constant, élargi seulement si la simulation est très longue."""
    return max(ANIMATION_STEP_MIN, end_time / MAX_FRAMES)


def describe_status(customer: Customer, time: float) -> str:
    """Situation d'un client à l'instant ``time``, en clair (légende du client suivi)."""
    if time < customer.arrival_time:
        return "pas encore arrivé"
    if customer.is_waiting_at(time):
        return f"en file depuis {format_minutes(time - customer.arrival_time)}"
    waited = format_minutes(customer.wait_time)
    if customer.is_being_served_at(time):
        return f"en caisse {customer.register_id} (a attendu {waited})"
    return f"parti (a attendu {waited})"


def wait_level(wait_so_far: float, threshold: float = WAIT_THRESHOLD_MIN) -> str:
    """Niveau d'alerte d'une attente : ok (vert), warning (orange), critical (rouge)."""
    if wait_so_far > threshold:
        return WAIT_CRITICAL
    if wait_so_far > threshold * WARNING_SHARE_OF_THRESHOLD:
        return WAIT_WARNING
    return WAIT_OK
