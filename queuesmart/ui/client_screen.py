"""Onglet « Écran client » : panneau des attentes estimées et parcours d'un client."""

import math

import streamlit as st

from queuesmart.domain.customer import Customer
from queuesmart.exceptions import UnknownCustomerError
from queuesmart.simulation.result import SimulationResult
from queuesmart.ui.client_board import BoardLine, build_board, format_minutes

TIME_STEP_MIN = 0.5

BOARD_CSS = """
<style>
.qs-tile {background:#111; color:#f5c518; border:3px solid #333; border-radius:10px;
          padding:12px 6px; text-align:center; font-family:monospace;}
.qs-tile.qs-best {border-color:#2ecc71; box-shadow:0 0 12px #2ecc71;}
.qs-register {color:#ddd; font-size:0.95rem;}
.qs-wait {font-size:1.5rem; font-weight:bold; margin:6px 0;}
.qs-queue {color:#aaa; font-size:0.85rem;}
.qs-badge {color:#2ecc71; font-weight:bold; font-size:0.8rem; min-height:1.2rem;}
</style>
"""


def render_client_screen(result: SimulationResult) -> None:
    """Ce que verrait un client en arrivant aux caisses, puis le suivi d'un client."""
    st.subheader("Écran client : temps d'attente estimé")
    time = _time_input(result)
    board = build_board(result.snapshot_at(time))
    _render_board(board)
    best = next(line for line in board if line.is_recommended)
    st.info(f"{format_minutes(time)} après l'ouverture : allez à la caisse {best.register_id}.")
    st.divider()
    _render_customer_journey(result)


def _time_input(result: SimulationResult) -> float:
    last_time = math.ceil(result.end_time / TIME_STEP_MIN) * TIME_STEP_MIN
    middle = round(last_time / 2 / TIME_STEP_MIN) * TIME_STEP_MIN
    return st.slider(
        "Instant affiché (minutes depuis l'ouverture)",
        0.0, last_time, middle, step=TIME_STEP_MIN, format="%.1f", key="client-screen-time",
    )


def _render_board(board: list[BoardLine]) -> None:
    st.markdown(BOARD_CSS, unsafe_allow_html=True)
    for column, line in zip(st.columns(len(board)), board, strict=True):
        column.markdown(_tile_html(line), unsafe_allow_html=True)


def _tile_html(line: BoardLine) -> str:
    css_class = "qs-tile qs-best" if line.is_recommended else "qs-tile"
    badge = "➜ CONSEILLÉE" if line.is_recommended else ""
    return (
        f"<div class='{css_class}'>"
        f"<div class='qs-register'>CAISSE {line.register_id}</div>"
        f"<div class='qs-wait'>{format_minutes(line.estimated_wait)}</div>"
        f"<div class='qs-queue'>{line.queue_length} client(s)</div>"
        f"<div class='qs-badge'>{badge}</div></div>"
    )


def _render_customer_journey(result: SimulationResult) -> None:
    st.markdown("#### Suivre un client")
    customer_id = st.number_input("Numéro du client", min_value=1, value=1, step=1)
    try:
        customer = result.customer(int(customer_id))
    except UnknownCustomerError as error:
        st.warning(str(error))
        return
    st.caption("Instants exprimés en temps écoulé depuis l'ouverture.")
    items = _journey_items(customer)
    for column, (label, value) in zip(st.columns(len(items)), items, strict=True):
        column.metric(label, value)


def _journey_items(customer: Customer) -> list[tuple[str, str]]:
    return [
        ("Arrivée", format_minutes(customer.arrival_time)),
        ("Caisse", f"n° {customer.register_id}"),
        ("Début du passage", format_minutes(customer.service_start)),
        ("Départ", format_minutes(customer.service_end)),
        ("Attente", format_minutes(customer.wait_time)),
    ]
