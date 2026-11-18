"""Plan du magasin pour la scène 2D. PUR : aucun import de Streamlit.

Repère en « cases » (unités de plan), origine en haut à gauche, y vers le bas :

    y = 0      mur de façade, porte de SORTIE en haut à droite
    y = 1.8    couloir de sortie (après les caisses)
    y = 4      poste de service : le client est servi à côté du tapis
    y = 6.2+   files d'attente, qui descendent vers les rayons
    y = 11.8   allée principale (on y arrive depuis l'ENTRÉE, à gauche)
    y > 13     rayons et meubles froids

Chaque caisse a sa propre allée verticale (x de la caisse) : les clients n'y
croisent ni tapis ni caissier. Les trajets passent par l'allée principale.
"""

from dataclasses import dataclass

REGISTER_COUNT = 5  # le moteur dynamique gère 1 à 5 caisses : on les dessine toutes
FIRST_LANE_X = 4.0
LANE_SPACING = 4.0
STORE_WIDTH = 24.0
STORE_HEIGHT = 24.0

FRONT_CORRIDOR_Y = 1.8
SERVICE_Y = 4.0
FIRST_SLOT_Y = 6.2
SLOT_SPACING = 0.78
SLOTS_PER_COLUMN = 6  # puis la file continue dans une colonne parallèle
COLUMN_SPACING = 1.0
COMPACT_COLUMN_SPACING = 0.9
MAIN_AISLE_Y = 11.8

ENTRANCE = (0.3, MAIN_AISLE_Y)
EXIT = (STORE_WIDTH - 1.0, 0.2)


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class SceneLayout:
    """Points d'ancrage (entrée, sortie, poste de service, places de file) et trajets."""

    def __init__(self, compact: bool = False):
        self.compact = compact

    entrance = Point(*ENTRANCE)
    exit = Point(*EXIT)

    def lane_x(self, register_id: int) -> float:
        """Abscisse de l'allée de la caisse ``register_id`` (1 à 5)."""
        if not 1 <= register_id <= REGISTER_COUNT:
            raise ValueError(f"Caisse {register_id} hors plan (1 à {REGISTER_COUNT}).")
        return FIRST_LANE_X + (register_id - 1) * LANE_SPACING

    def service_spot(self, register_id: int) -> Point:
        """Place du client en train de payer."""
        return Point(self.lane_x(register_id), SERVICE_Y)

    def queue_slot(self, register_id: int, rank: int) -> Point:
        """Place du client en attente (1 = tête de file).

        En mode compact, au-delà de 18 clients, coordonnées virtuelles bornées et distinctes.
        L'atelier agrège ces clients en un badge ; le moteur les conserve tous.
        """
        if rank < 1:
            raise ValueError("Le rang dans la file commence à 1.")
        column, row = divmod(rank - 1, SLOTS_PER_COLUMN)
        if not self.compact:
            return Point(
                self.lane_x(register_id) + column * COLUMN_SPACING,
                FIRST_SLOT_Y + row * SLOT_SPACING,
            )
        return Point(
            self.lane_x(register_id) + (column % 3) * COMPACT_COLUMN_SPACING,
            FIRST_SLOT_Y + row * SLOT_SPACING + (column // 3) * 0.002,
        )

    def route(self, start: Point, end: Point) -> list[Point]:
        """Trajet par l'allée principale, pour ne jamais traverser une autre file."""
        if abs(start.x - end.x) < 1e-9:
            return [end]
        return [Point(start.x, MAIN_AISLE_Y), Point(end.x, MAIN_AISLE_Y), end]

    def exit_route(self, register_id: int) -> list[Point]:
        """De la caisse à la porte de sortie, par le couloir de façade."""
        lane = self.lane_x(register_id)
        return [Point(lane, FRONT_CORRIDOR_Y), Point(self.exit.x, FRONT_CORRIDOR_Y), self.exit]

    def abandon_route(self, start: Point) -> list[Point]:
        """Un client qui abandonne repart par l'entrée, sans passer en caisse."""
        return [Point(start.x, MAIN_AISLE_Y), self.entrance]

    def to_dict(self) -> dict:
        """Ce dont le dessin JavaScript a besoin (aucune règle métier)."""
        return {
            "width": STORE_WIDTH,
            "height": STORE_HEIGHT,
            "registers": [
                {"id": rid, "lane_x": self.lane_x(rid)} for rid in range(1, REGISTER_COUNT + 1)
            ],
            "service_y": SERVICE_Y,
            "first_slot_y": FIRST_SLOT_Y,
            "front_corridor_y": FRONT_CORRIDOR_Y,
            "main_aisle_y": MAIN_AISLE_Y,
            "entrance": [self.entrance.x, self.entrance.y],
            "exit": [self.exit.x, self.exit.y],
        }
