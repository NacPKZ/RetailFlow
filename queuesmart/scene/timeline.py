"""Rejeu des événements du moteur dynamique en trajectoires pour la scène 2D.

La simulation est entièrement terminée en Python avant la lecture. Ce module ne
prend AUCUNE décision métier : il lit ``DynamicResult.events`` dans l'ordre et
traduit chaque événement en déplacements visuels. Le JavaScript se contente
ensuite d'échantillonner ces trajectoires à l'instant affiché.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from queuesmart.scene.layout import REGISTER_COUNT, Point, SceneLayout
from queuesmart.scene.queue_board import QueueBoard
from queuesmart.scene.tracks import (
    ABANDONING,
    ENTERING,
    GONE,
    IN_QUEUE,
    IN_SERVICE,
    LEAVING,
    SWITCHING,
    CustomerTrack,
)
from queuesmart.simulation.dynamic import DynamicEvent, DynamicResult

DECIMALS = 3  # précision envoyée au navigateur (suffisante à l'écran, JSON plus léger)


@dataclass(frozen=True)
class RegisterState:
    """État d'une caisse à partir de ``time`` : ouverte ? quel client est servi ?"""

    time: float
    is_open: bool
    serving_customer_id: int | None


@dataclass(frozen=True)
class SceneTimeline:
    """Tout ce que la scène doit afficher, calculé une fois pour toute la lecture."""

    end_time: float
    tracks: dict[int, CustomerTrack]
    register_states: dict[int, list[RegisterState]]
    served_at: dict[int, float]
    abandoned_at: dict[int, float]

    def to_dict(self, layout: SceneLayout) -> dict:
        """Données sérialisables en JSON pour ``frontend_2d``."""
        return {
            "layout": layout.to_dict(),
            "end_time": round(self.end_time, DECIMALS),
            "customers": [_track_to_dict(track) for track in self.tracks.values()],
            "registers": {
                str(rid): [[_r(s.time), s.is_open, s.serving_customer_id] for s in states]
                for rid, states in self.register_states.items()
            },
            "served_at": {str(cid): _r(t) for cid, t in self.served_at.items()},
            "abandoned_at": {str(cid): _r(t) for cid, t in self.abandoned_at.items()},
        }


class SceneTimelineBuilder:
    """Traduit la séquence d'événements en trajectoires (un gestionnaire par type)."""

    def __init__(self, layout: SceneLayout | None = None) -> None:
        self._layout = layout or SceneLayout()
        self._handlers: dict[str, Callable[[DynamicEvent], None]] = {
            "customer_arrived": self._on_arrived,
            "queue_joined": self._on_queue_joined,
            "service_started": self._on_service_started,
            "customer_departed": self._on_departed,
            "queue_switched": self._on_switched,
            "customer_abandoned": self._on_abandoned,
            "register_opened": self._on_register_change,
            "register_closed": self._on_register_change,
        }

    def build(self, result: DynamicResult) -> SceneTimeline:
        return self.replay(result.events, result.config.open_registers)

    def replay(self, events: Iterable[DynamicEvent], initially_open: int) -> SceneTimeline:
        """Rejoue les événements une seule fois chacun, dans leur ordre d'origine."""
        self._board = QueueBoard(REGISTER_COUNT, initially_open)
        self._tracks: dict[int, CustomerTrack] = {}
        self._served_at: dict[int, float] = {}
        self._abandoned_at: dict[int, float] = {}
        self._register_states = {
            rid: [RegisterState(0.0, self._board.is_open(rid), None)]
            for rid in range(1, REGISTER_COUNT + 1)
        }
        end_time = 0.0
        for event in events:
            self._handlers[event.type](event)
            end_time = max(end_time, event.time)
        last_move = max((t.keyframes[-1].time for t in self._tracks.values()), default=0.0)
        return SceneTimeline(
            end_time=max(end_time, last_move),
            tracks=self._tracks,
            register_states=self._register_states,
            served_at=self._served_at,
            abandoned_at=self._abandoned_at,
        )

    # --- Gestionnaires d'événements ---------------------------------------------------

    def _on_arrived(self, event: DynamicEvent) -> None:
        self._tracks[event.customer_id] = CustomerTrack(
            event.customer_id, event.time, self._layout.entrance, ENTERING
        )

    def _on_queue_joined(self, event: DynamicEvent) -> None:
        self._board.join(event.register_id, event.customer_id)
        self._walk_to_queue(event, event.register_id, moving=ENTERING)

    def _on_service_started(self, event: DynamicEvent) -> None:
        self._board.start_service(event.register_id, event.customer_id)
        track = self._tracks[event.customer_id]
        spot = self._layout.service_spot(event.register_id)
        track.move(event.time, self._route_from(track, event.time, spot), IN_SERVICE, IN_SERVICE)
        self._compact_queue(event.register_id, event.time)
        self._record_register(event.register_id, event.time)

    def _on_departed(self, event: DynamicEvent) -> None:
        self._board.end_service(event.register_id)
        self._served_at[event.customer_id] = event.time
        route = self._layout.exit_route(event.register_id)
        self._tracks[event.customer_id].move(event.time, route, LEAVING, GONE)
        self._record_register(event.register_id, event.time)

    def _on_switched(self, event: DynamicEvent) -> None:
        self._board.leave(event.register_id, event.customer_id)
        self._compact_queue(event.register_id, event.time)
        self._board.join(event.target_register_id, event.customer_id)
        self._walk_to_queue(event, event.target_register_id, moving=SWITCHING)

    def _on_abandoned(self, event: DynamicEvent) -> None:
        self._board.leave(event.register_id, event.customer_id)
        self._abandoned_at[event.customer_id] = event.time
        track = self._tracks[event.customer_id]
        start = track.position_at(event.time) or self._layout.entrance
        track.move(event.time, self._layout.abandon_route(start), ABANDONING, GONE)
        self._compact_queue(event.register_id, event.time)

    def _on_register_change(self, event: DynamicEvent) -> None:
        self._board.set_open(event.register_id, event.type == "register_opened")
        self._record_register(event.register_id, event.time)

    # --- Outils communs (DRY) ---------------------------------------------------------

    def _walk_to_queue(self, event: DynamicEvent, register_id: int, moving: str) -> None:
        """Envoie le client à la dernière place de la file ``register_id``."""
        track = self._tracks[event.customer_id]
        rank = self._board.rank(register_id, event.customer_id)
        slot = self._layout.queue_slot(register_id, rank)
        track.move(event.time, self._route_from(track, event.time, slot), moving, IN_QUEUE)

    def _compact_queue(self, register_id: int, time: float) -> None:
        """Fait avancer chaque client restant à sa nouvelle place (pas de trou, pas de doublon)."""
        for rank, customer_id in enumerate(self._board.waiting(register_id), start=1):
            track = self._tracks[customer_id]
            slot = self._layout.queue_slot(register_id, rank)
            if track.keyframes[-1].position == slot:
                continue
            state = track.state_at(time) or IN_QUEUE
            if state == IN_QUEUE:  # déjà dans la file : il avance simplement d'une place
                track.move(time, [slot], IN_QUEUE, IN_QUEUE)
            else:  # encore en chemin : il garde son trajet par l'allée principale
                track.move(time, self._route_from(track, time, slot), state, IN_QUEUE)

    def _route_from(self, track: CustomerTrack, time: float, destination: Point) -> list[Point]:
        start = track.position_at(time) or track.keyframes[-1].position
        return self._layout.route(start, destination)

    def _record_register(self, register_id: int, time: float) -> None:
        self._register_states[register_id].append(
            RegisterState(time, self._board.is_open(register_id), self._board.serving(register_id))
        )


def _r(value: float) -> float:
    return round(value, DECIMALS)


def _track_to_dict(track: CustomerTrack) -> dict:
    return {
        "id": track.customer_id,
        "keyframes": [
            [_r(k.time), _r(k.position.x), _r(k.position.y), k.state] for k in track.keyframes
        ],
    }
