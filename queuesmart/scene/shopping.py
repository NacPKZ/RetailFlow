"""Parcours d'achat synthétiques précédant l'arrivée dans la zone des caisses.

Ces parcours illustrent les courses ; ils ne modifient pas les temps d'arrivée
aux caisses calculés par le moteur. Certains clients font déjà leurs courses à t=0.
"""

from queuesmart.scene.layout import SceneLayout
from queuesmart.simulation.dynamic import DynamicResult


def shopping_tracks(result: DynamicResult) -> list[dict]:
    layout = SceneLayout()
    tracks = []
    aisles = [1.0, 5.2, 9.5, 13.8, 18.1, 22.8]
    for c in result.customers:
        duration = 4.0 + c.customer_id % 7
        start = c.arrival_time - duration
        x = aisles[c.customer_id % len(aisles)]
        y = 15.2 + (c.customer_id % 4) * 1.4
        waypoints = [
            (0.0, layout.entrance.x, layout.entrance.y),
            (0.16, x, layout.entrance.y),
            (0.38, x, y),
            (0.58, x, y),
            (0.77, x, layout.entrance.y),
            (0.97, layout.entrance.x, layout.entrance.y),
            (1.0, layout.entrance.x, layout.entrance.y),
        ]
        frames = [
            [round(start + duration * phase, 4), px, py, "parti" if phase == 1 else "courses"]
            for phase, px, py in waypoints
        ]
        tracks.append(
            {"id": c.customer_id, "start": start, "end": c.arrival_time, "keyframes": frames}
        )
    return tracks
