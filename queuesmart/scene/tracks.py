"""Trajectoire d'un client : une suite d'images clés (temps, position, état).

Entre deux images clés, la position est interpolée linéairement. L'état d'un
segment est celui de son image clé de départ. Ce calcul est le même côté
JavaScript (``frontend_2d/animations.js``) : la scène ne fait qu'échantillonner.
"""

from dataclasses import dataclass

from queuesmart.config import MIN_SERVICE_TIME_MIN
from queuesmart.scene.layout import Point

WALK_SPEED = 30.0  # cases par minute simulée
# Un trajet visuel dure toujours moins qu'un passage en caisse : un client arrivé
# devant une caisse libre l'atteint donc avant la fin de son service.
MAX_TRAVEL_MIN = 0.9 * MIN_SERVICE_TIME_MIN

# États graphiques (cf. dossier de mission, section 5)
ENTERING = "entrant"
IN_QUEUE = "en_file"
IN_SERVICE = "en_service"
SWITCHING = "en_transfert"
ABANDONING = "abandon"
LEAVING = "sortant"
GONE = "parti"


@dataclass(frozen=True)
class Keyframe:
    time: float
    position: Point
    state: str


class CustomerTrack:
    """Positions successives d'un client. Rien n'est affiché avant la 1re image clé."""

    def __init__(self, customer_id: int, time: float, position: Point, state: str) -> None:
        self.customer_id = customer_id
        self._keyframes = [Keyframe(time, position, state)]

    @property
    def keyframes(self) -> tuple[Keyframe, ...]:
        return tuple(self._keyframes)

    def position_at(self, time: float) -> Point | None:
        """Position à l'instant ``time`` ; None si le client n'est pas (ou plus) visible."""
        index = self._segment_index(time)
        if index is None or self._keyframes[index].state == GONE:
            return None
        current = self._keyframes[index]
        if index + 1 == len(self._keyframes):
            return current.position
        following = self._keyframes[index + 1]
        progress = (time - current.time) / (following.time - current.time)
        return _lerp(current.position, following.position, progress)

    def state_at(self, time: float) -> str | None:
        index = self._segment_index(time)
        return None if index is None else self._keyframes[index].state

    def move(self, time: float, waypoints: list[Point], moving: str, settled: str) -> None:
        """Part de la position actuelle à ``time`` et suit ``waypoints``.

        Un trajet encore en cours est interrompu : on repart de là où le client
        se trouve vraiment (pas de saut). Pendant le trajet l'état vaut
        ``moving`` ; à l'arrivée il vaut ``settled``.
        """
        start = self.position_at(time) or self._keyframes[-1].position
        self._keyframes = [k for k in self._keyframes if k.time < time]
        path = [start, *(p for p in waypoints)]
        lengths = [a.distance_to(b) for a, b in zip(path, path[1:], strict=False)]
        total = sum(lengths)
        if total == 0:
            self._keyframes.append(Keyframe(time, start, settled))
            return
        duration = min(total / WALK_SPEED, MAX_TRAVEL_MIN)
        self._keyframes.append(Keyframe(time, start, moving))
        elapsed = 0.0
        for point, length in zip(path[1:-1], lengths, strict=False):
            elapsed += length
            self._keyframes.append(Keyframe(time + duration * elapsed / total, point, moving))
        self._keyframes.append(Keyframe(time + duration, path[-1], settled))

    def _segment_index(self, time: float) -> int | None:
        """Indice de la dernière image clé déjà atteinte à l'instant ``time``."""
        started = [index for index, k in enumerate(self._keyframes) if k.time <= time]
        return started[-1] if started else None


def _lerp(start: Point, end: Point, progress: float) -> Point:
    progress = min(max(progress, 0.0), 1.0)
    return Point(start.x + (end.x - start.x) * progress, start.y + (end.y - start.y) * progress)
