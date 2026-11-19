"""Séries et performances calculées à partir du journal du moteur dynamique."""

from itertools import groupby
from operator import attrgetter

import pandas as pd

from queuesmart.analytics.dynamic_metrics import observation_end, resource_frame
from queuesmart.scene.queue_board import QueueBoard
from queuesmart.simulation.dynamic import DynamicResult

REGISTER_IDS = range(1, 6)


def queue_frame(result: DynamicResult) -> pd.DataFrame:
    """Photographier les cinq caisses après tous les événements d'une même minute."""
    board = QueueBoard(len(REGISTER_IDS), result.config.open_registers)
    arrived = served = abandoned = 0
    rows = []

    def snapshot(time):
        rows.extend(
            {
                "Minute": time,
                "Caisse": rid,
                "En file": len(board.waiting(rid)),
                "En service": int(board.serving(rid) is not None),
                "Ouverte": board.is_open(rid),
                "Arrivés": arrived,
                "Servis": served,
                "Abandons": abandoned,
            }
            for rid in REGISTER_IDS
        )

    if not result.events or result.events[0].time > 0:
        snapshot(0.0)
    horizon = observation_end(result)
    for time, events in groupby(result.events, key=attrgetter("time")):
        if time > horizon:
            break
        for event in events:
            rid, cid = event.register_id, event.customer_id
            match event.type:
                case "customer_arrived":
                    arrived += 1
                case "queue_joined":
                    board.join(rid, cid)
                case "service_started":
                    board.start_service(rid, cid)
                case "customer_departed":
                    board.end_service(rid)
                    served += 1
                case "queue_switched":
                    board.leave(rid, cid)
                    board.join(event.target_register_id, cid)
                case "customer_abandoned":
                    board.leave(rid, cid)
                    abandoned += 1
                case "register_opened" | "register_closed":
                    board.set_open(rid, event.type == "register_opened")
        snapshot(time)
    return pd.DataFrame(rows)


def register_performance(result: DynamicResult, queues: pd.DataFrame) -> pd.DataFrame:
    """Attribuer chaque service terminé à la caisse de sortie."""
    completions = (
        pd.DataFrame(
            [
                (c.register_id, c.wait_time)
                for c in result.customers
                if c.departure_time is not None
            ],
            columns=["Caisse", "Attente"],
            dtype=float,
        )
        .groupby("Caisse")["Attente"]
        .agg(["count", "mean"])
    )
    return resource_frame(result).assign(
        Servis=lambda frame: frame["Caisse"].map(completions["count"]).fillna(0).astype(int),
        **{"Attente moyenne": lambda frame: frame["Caisse"].map(completions["mean"])},
        **{
            "Pic de file": lambda frame: frame["Caisse"].map(
                queues.groupby("Caisse")["En file"].max()
            )
        },
    )
