"""Contenu du panneau « temps d'attente estimé ». PUR : aucun import de Streamlit."""

from dataclasses import dataclass

from queuesmart.simulation.result import StoreSnapshot

SECONDS_PER_MINUTE = 60


@dataclass(frozen=True)
class BoardLine:
    """Une ligne (une tuile) du panneau d'affichage."""

    register_id: int
    estimated_wait: float
    queue_length: int
    is_recommended: bool


def build_board(snapshot: StoreSnapshot) -> list[BoardLine]:
    """Lignes du panneau. Caisse conseillée : attente minimale, puis plus petit numéro.

    Même règle que le comportement « least_wait » : l'écran conseille ce que
    le client suivrait.
    """
    best = min(snapshot.registers, key=lambda r: (r.estimated_wait, r.register_id))
    return [
        BoardLine(
            register_id=register.register_id,
            estimated_wait=register.estimated_wait,
            queue_length=register.queue_length,
            is_recommended=register.register_id == best.register_id,
        )
        for register in snapshot.registers
    ]


def format_minutes(minutes: float) -> str:
    """Durée lisible : « 2 min 30 s », « 45 s », « 3 min ». Utilisé par tous les onglets."""
    if minutes < 0:
        raise ValueError("Une durée ne peut pas être négative.")
    whole_minutes, seconds = divmod(round(minutes * SECONDS_PER_MINUTE), SECONDS_PER_MINUTE)
    if whole_minutes == 0:
        return f"{seconds} s" if seconds else "0 min"
    if seconds == 0:
        return f"{whole_minutes} min"
    return f"{whole_minutes} min {seconds} s"
