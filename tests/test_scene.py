"""Tests de réception de la scène 2D (dossier de mission, section 7).

V07 (fluidité à l'écran) et V09 (redimensionnement) se vérifient dans le navigateur ;
ici on teste tout ce qui relève du calcul : V01 à V06, V08, V10 et le coût de V07.
"""

import json
from time import perf_counter

import pytest

from queuesmart.config import ScenarioConfig
from queuesmart.scene.layout import MAIN_AISLE_Y, SLOTS_PER_COLUMN, Point, SceneLayout
from queuesmart.scene.queue_board import QueueBoard
from queuesmart.scene.timeline import SceneTimelineBuilder
from queuesmart.scene.tracks import (
    ABANDONING,
    GONE,
    IN_QUEUE,
    IN_SERVICE,
    MAX_TRAVEL_MIN,
    SWITCHING,
    CustomerTrack,
)
from queuesmart.simulation.dynamic import DynamicEvent, DynamicOptions, DynamicSimulationEngine

LAYOUT = SceneLayout()
SETTLE = MAX_TRAVEL_MIN + 0.01  # après ce délai, tout trajet visuel est terminé


def run(customers: int, registers: int, **options):
    config = ScenarioConfig("Scène", customers, 30.0, 2.0, registers, seed=42)
    return DynamicSimulationEngine().run(config, DynamicOptions(**options))


def ev(time, kind, cid=None, rid=None, target=None, position=None) -> DynamicEvent:
    return DynamicEvent(time, kind, cid, rid, target, position)


def arrive(time, cid, rid, position):
    joined = ev(time, "queue_joined", cid, rid, position=position)
    return [ev(time, "customer_arrived", cid), joined]


# --- Plan ------------------------------------------------------------------------------


def test_queue_slots_are_distinct_and_behind_the_service_spot() -> None:
    slots = [LAYOUT.queue_slot(1, rank) for rank in range(1, 3 * SLOTS_PER_COLUMN)]
    assert len(set(slots)) == len(slots)
    assert all(slot.y > LAYOUT.service_spot(1).y for slot in slots)


@pytest.mark.parametrize("register_id", [0, 6])
def test_unknown_register_is_rejected(register_id: int) -> None:
    with pytest.raises(ValueError):
        LAYOUT.lane_x(register_id)


def test_route_goes_through_main_aisle_to_change_lane() -> None:
    route = LAYOUT.route(LAYOUT.queue_slot(1, 3), LAYOUT.queue_slot(4, 1))
    assert [p.y for p in route[:2]] == [MAIN_AISLE_Y, MAIN_AISLE_Y]
    head = LAYOUT.queue_slot(2, 1)
    assert LAYOUT.route(LAYOUT.queue_slot(2, 2), head) == [head]


# --- Trajectoires ----------------------------------------------------------------------


def test_track_interpolates_and_is_invisible_before_and_after() -> None:
    track = CustomerTrack(1, 2.0, Point(0, 0), IN_QUEUE)
    track.move(2.0, [Point(3, 4)], IN_QUEUE, GONE)  # 5 cases -> 5/30 min
    assert track.position_at(1.9) is None
    middle = track.position_at(2.0 + 5 / 60)
    assert (middle.x, middle.y) == pytest.approx((1.5, 2.0))
    assert track.position_at(10.0) is None


def test_interrupted_move_restarts_from_current_position() -> None:
    track = CustomerTrack(1, 0.0, Point(0, 0), IN_QUEUE)
    track.move(0.0, [Point(3, 0)], IN_QUEUE, IN_QUEUE)  # 3 cases -> 0,1 min de trajet
    track.move(0.05, [Point(0, 0)], IN_QUEUE, IN_QUEUE)  # demi-tour à mi-chemin
    assert track.position_at(0.05).x == pytest.approx(1.5)
    assert track.position_at(0.05 + 0.05).x == pytest.approx(0.0)


def test_queue_board_rejects_customer_absent_from_queue() -> None:
    with pytest.raises(ValueError):
        QueueBoard(5, 1).leave(1, 99)


# --- V01 : 1 caisse, 5 clients ------------------------------------------------------


def test_v01_fifo_order_and_departures() -> None:
    result = run(5, 1, patience_min=None)
    timeline = SceneTimelineBuilder().build(result)
    started = [e.customer_id for e in result.events if e.type == "service_started"]
    assert started == sorted(started)
    assert set(timeline.served_at) == {1, 2, 3, 4, 5}
    for track in timeline.tracks.values():
        assert track.keyframes[-1].state == GONE
        assert track.keyframes[-1].position == LAYOUT.exit


# --- V02 : 3 caisses, 30 clients, graine fixe ---------------------------------------


def test_v02_each_customer_goes_to_the_register_chosen_by_the_engine() -> None:
    result = run(30, 3)
    timeline = SceneTimelineBuilder().build(result)
    for event in result.events:
        if event.type == "service_started":
            track = timeline.tracks[event.customer_id]
            at_till = [k for k in track.keyframes if k.state == IN_SERVICE
                       and k.position == LAYOUT.service_spot(event.register_id)]
            assert at_till, f"le client {event.customer_id} n'atteint pas sa caisse"
            assert track.state_at(event.time) == IN_SERVICE


def test_v02_recomputed_rank_matches_engine_position_on_join() -> None:
    result = run(30, 3)
    board = QueueBoard(5, 3)
    for event in result.events:
        if event.type == "queue_joined":
            board.join(event.register_id, event.customer_id)
            assert board.rank(event.register_id, event.customer_id) == event.queue_position
        elif event.type == "service_started":
            board.start_service(event.register_id, event.customer_id)
        elif event.type in ("customer_abandoned", "queue_switched"):
            board.leave(event.register_id, event.customer_id)
            if event.target_register_id:
                board.join(event.target_register_id, event.customer_id)


# --- V03 : avancement sans superposition ---------------------------------------------


def test_v03_queue_moves_forward_when_head_is_served() -> None:
    events = [*arrive(0.0, 1, 1, 1), ev(0.0, "service_started", 1, 1),
              *arrive(0.1, 2, 1, 1), *arrive(0.2, 3, 1, 2),
              ev(2.0, "customer_departed", 1, 1), ev(2.0, "service_started", 2, 1)]
    tracks = SceneTimelineBuilder().replay(events, initially_open=1).tracks
    assert tracks[3].position_at(1.9) == LAYOUT.queue_slot(1, 2)
    assert tracks[3].position_at(2.0 + SETTLE) == LAYOUT.queue_slot(1, 1)
    assert tracks[2].position_at(2.0 + SETTLE) == LAYOUT.service_spot(1)


def test_v03_no_two_settled_customers_share_a_spot() -> None:
    result = run(100, 3)
    timeline = SceneTimelineBuilder().build(result)
    for event in result.events:
        moment = event.time + SETTLE
        spots = [t.position_at(moment) for t in timeline.tracks.values()
                 if t.state_at(moment) in (IN_QUEUE, IN_SERVICE)]
        assert len(spots) == len(set(spots)), f"Superposition à t = {moment:.2f}"


# --- V04 : changement de file ---------------------------------------------------------


def test_v04_switch_updates_both_queues() -> None:
    events = [*arrive(0.0, 1, 1, 1), ev(0.0, "service_started", 1, 1),
              *arrive(0.1, 2, 1, 1), *arrive(0.2, 3, 1, 2),
              *arrive(0.3, 4, 2, 1), ev(0.3, "service_started", 4, 2),
              *arrive(0.4, 5, 2, 1),
              ev(1.0, "queue_switched", 2, 1, target=2, position=2)]
    tracks = SceneTimelineBuilder().replay(events, initially_open=2).tracks
    assert tracks[2].state_at(1.0) == SWITCHING
    assert tracks[2].position_at(1.0 + SETTLE) == LAYOUT.queue_slot(2, 2)  # derrière le client 5
    assert tracks[3].position_at(1.0 + SETTLE) == LAYOUT.queue_slot(1, 1)  # avance d'une place


# --- V05 : abandon --------------------------------------------------------------------


def test_v05_abandon_leaves_without_service() -> None:
    result = run(60, 1, patience_min=2.0, switching_enabled=False)
    timeline = SceneTimelineBuilder().build(result)
    assert timeline.abandoned_at
    for customer_id, abandoned_at in timeline.abandoned_at.items():
        track = timeline.tracks[customer_id]
        assert track.state_at(abandoned_at) == ABANDONING
        assert IN_SERVICE not in {k.state for k in track.keyframes}
        assert track.keyframes[-1].position == LAYOUT.entrance
        assert customer_id not in timeline.served_at


# --- V06 : fermeture avec service en cours -------------------------------------------


def test_v06_closing_does_not_interrupt_service() -> None:
    result = run(60, 2, register_changes=((5.0, 2, False),))
    timeline = SceneTimelineBuilder().build(result)
    closed = next(e for e in result.events if e.type == "register_closed")
    states = timeline.register_states[2]
    at_closing = next(s for s in states if s.time == closed.time and not s.is_open)
    serving = at_closing.serving_customer_id
    assert serving is not None, "le scénario doit fermer une caisse occupée"
    departure = next(e for e in result.events
                     if e.type == "customer_departed" and e.customer_id == serving)
    assert departure.time > closed.time
    assert timeline.tracks[serving].state_at(departure.time - 0.01) == IN_SERVICE


# --- V07 : 100 clients, 5 caisses (coût du calcul) ------------------------------------


def test_v07_full_scene_is_cheap_to_build_and_send() -> None:
    result = run(100, 5)
    start = perf_counter()
    timeline = SceneTimelineBuilder().build(result)
    payload = json.dumps(timeline.to_dict(LAYOUT))
    assert perf_counter() - start < 1.0
    assert len(payload) < 500_000


# --- V08 : rejeu ----------------------------------------------------------------------


def test_v08_replaying_the_same_events_gives_the_same_scene() -> None:
    result = run(60, 3, register_changes=((4.0, 3, False),))
    first = SceneTimelineBuilder().build(result).to_dict(LAYOUT)
    second = SceneTimelineBuilder().build(result).to_dict(LAYOUT)
    assert first == second


# --- V10 : pause, reprise, retour en arrière -----------------------------------------


def test_v10_seek_order_does_not_change_what_is_displayed() -> None:
    timeline = SceneTimelineBuilder().build(run(60, 3))
    moments = [i * 0.37 for i in range(int(timeline.end_time / 0.37) + 1)]

    def frame(t):
        return {cid: track.position_at(t) for cid, track in timeline.tracks.items()}

    forward = {t: frame(t) for t in moments}
    backward = {t: frame(t) for t in reversed(moments)}
    assert forward == backward


def test_v10_every_event_is_applied_exactly_once() -> None:
    result = run(60, 3)
    timeline = SceneTimelineBuilder().build(result)
    departed = [e.customer_id for e in result.events if e.type == "customer_departed"]
    assert sorted(departed) == sorted(timeline.served_at)
    assert len(timeline.served_at) + len(timeline.abandoned_at) == len(result.customers)
