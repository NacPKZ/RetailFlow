"""Onglet « Magasin 2D » : animation Plotly de la vue du dessus.

Ce module ne fait que du dessin : les positions viennent de ``StoreLayout`` (pur, testé).
"""

import plotly.graph_objects as go
import streamlit as st

from queuesmart.simulation.result import SimulationResult, StoreSnapshot
from queuesmart.ui.client_board import format_minutes
from queuesmart.ui.store_layout import (
    QUEUE_SPACING,
    WAIT_CRITICAL,
    WAIT_OK,
    WAIT_WARNING,
    PlacedCustomer,
    StoreLayout,
    animation_step,
    describe_status,
    wait_level,
)

FRAME_DURATION_MS = 150
FIGURE_HEIGHT_PX = 620
PLOT_MARGIN = 1.0

WAIT_COLORS = {WAIT_OK: "#2ca02c", WAIT_WARNING: "#ff7f0e", WAIT_CRITICAL: "#d62728"}
REGISTER_COLOR = "#4c78a8"
FOLLOWED_COLOR = "#9467bd"
REGISTER_SIZE = 44
CUSTOMER_SIZE = 14
FOLLOWED_SIZE = 26


def render_store_view(result: SimulationResult) -> None:
    """Animation du magasin, avec la possibilité de suivre un client."""
    st.subheader("Vue du dessus du magasin")
    followed_id = _followed_customer_input(result)
    st.caption(
        "Vert : attente courte · Orange : plus de la moitié du seuil (5 min) · "
        "Rouge : au-delà du seuil. Le client suivi est entouré en violet."
    )
    st.plotly_chart(_build_figure(result, followed_id))


def _followed_customer_input(result: SimulationResult) -> int | None:
    options = [None, *(customer.customer_id for customer in result.customers)]
    return st.selectbox(
        "Suivre un client",
        options,
        format_func=lambda cid: "Aucun" if cid is None else f"Client n°{cid}",
    )


def _build_figure(result: SimulationResult, followed_id: int | None) -> go.Figure:
    layout = StoreLayout(result.config.open_registers)
    snapshots = result.timeline(animation_step(result.end_time))
    frames = [
        _frame(index, snapshot, layout, result, followed_id)
        for index, snapshot in enumerate(snapshots)
    ]
    last_register_x, _ = layout.register_position(result.config.open_registers)
    lowest_y = -_longest_queue(snapshots) * QUEUE_SPACING
    figure = go.Figure(data=frames[0].data, frames=frames)
    figure.update_layout(
        title_text=frames[0].layout.title.text,
        height=FIGURE_HEIGHT_PX,
        showlegend=False,
        xaxis=_axis(-PLOT_MARGIN, last_register_x + PLOT_MARGIN),
        yaxis=_axis(lowest_y - PLOT_MARGIN, 2 * PLOT_MARGIN),
        updatemenus=_play_buttons(),
        sliders=[_time_slider(snapshots)],
    )
    return figure


def _frame(
    index: int,
    snapshot: StoreSnapshot,
    layout: StoreLayout,
    result: SimulationResult,
    followed_id: int | None,
) -> go.Frame:
    placed = layout.place_customers(snapshot, result)
    followed = [p for p in placed if p.customer_id == followed_id]
    return go.Frame(
        name=str(index),
        data=[
            _registers_trace(snapshot, layout),
            _customers_trace(placed),
            _followed_trace(followed),
        ],
        layout=go.Layout(title_text=_frame_title(snapshot, result, followed_id)),
    )


def _registers_trace(snapshot: StoreSnapshot, layout: StoreLayout) -> go.Scatter:
    positions = [layout.register_position(r.register_id) for r in snapshot.registers]
    return go.Scatter(
        x=[x for x, _ in positions],
        y=[y for _, y in positions],
        mode="markers+text",
        marker={"symbol": "square", "size": REGISTER_SIZE, "color": REGISTER_COLOR},
        text=[f"Caisse {r.register_id}<br>{format_minutes(r.estimated_wait)}"
              for r in snapshot.registers],
        textposition="top center",
        hoverinfo="skip",
    )


def _customers_trace(placed: list[PlacedCustomer]) -> go.Scatter:
    return go.Scatter(
        x=[p.x for p in placed],
        y=[p.y for p in placed],
        mode="markers",
        marker={"size": CUSTOMER_SIZE,
                "color": [WAIT_COLORS[wait_level(p.wait_so_far)] for p in placed]},
        hovertext=[f"Client n°{p.customer_id} · attente {format_minutes(p.wait_so_far)}"
                   for p in placed],
        hoverinfo="text",
    )


def _followed_trace(followed: list[PlacedCustomer]) -> go.Scatter:
    return go.Scatter(
        x=[p.x for p in followed],
        y=[p.y for p in followed],
        mode="markers",
        marker={"symbol": "circle-open", "size": FOLLOWED_SIZE,
                "line": {"width": 4, "color": FOLLOWED_COLOR}},
        hoverinfo="skip",
    )


def _frame_title(snapshot: StoreSnapshot, result: SimulationResult, followed_id: int | None) -> str:
    title = (
        f"t = {format_minutes(snapshot.time)} · pas encore arrivés : {snapshot.not_arrived_count}"
        f" · partis : {snapshot.departed_count}"
    )
    if followed_id is None:
        return title
    status = describe_status(result.customer(followed_id), snapshot.time)
    return f"{title}<br>Client n°{followed_id} : {status}"


def _longest_queue(snapshots: list[StoreSnapshot]) -> int:
    return max(len(r.waiting_customer_ids) for s in snapshots for r in s.registers)


def _axis(low: float, high: float) -> dict:
    return {"range": [low, high], "visible": False, "fixedrange": True}


def _animate_args(frame_names: list[str] | None, duration_ms: int) -> list:
    options = {"frame": {"duration": duration_ms, "redraw": True},
               "mode": "immediate", "fromcurrent": True, "transition": {"duration": 0}}
    return [frame_names, options]


def _play_buttons() -> list[dict]:
    play = {"label": "▶ Lecture", "method": "animate",
            "args": _animate_args(None, FRAME_DURATION_MS)}
    pause = {"label": "⏸ Pause", "method": "animate", "args": _animate_args([None], 0)}
    return [{"type": "buttons", "direction": "left", "x": 0.0, "y": 0.0,
             "xanchor": "left", "yanchor": "top", "buttons": [play, pause]}]


def _time_slider(snapshots: list[StoreSnapshot]) -> dict:
    steps = [
        {"label": f"{snapshot.time:.1f}", "method": "animate",
         "args": _animate_args([str(index)], 0)}
        for index, snapshot in enumerate(snapshots)
    ]
    return {"active": 0, "steps": steps, "x": 0.18, "len": 0.82, "y": 0.0,
            "currentvalue": {"prefix": "Temps (min) : "}}
