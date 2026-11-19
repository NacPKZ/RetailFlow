"""Présentation partagée et rendu des graphiques."""

from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from queuesmart.ui.charts import PLOT_CONFIG


def theme() -> None:
    css = (Path(__file__).parent / "assets" / "retailflow.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def section(title: str, caption: str = "") -> None:
    st.markdown(
        f'<div class="rf-section"><strong>{escape(title)}</strong>'
        f"<span>{escape(caption)}</span></div>",
        unsafe_allow_html=True,
    )


def plot(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key=key)


def cards(values: list[tuple[str, str, str, str]]) -> None:
    content = "".join(
        f'<div class="rf-card" style="--accent:{color}">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div><div class="hint">{escape(hint)}</div></div>'
        for label, value, hint, color in values
    )
    st.markdown(f'<div class="rf-card-grid">{content}</div>', unsafe_allow_html=True)
