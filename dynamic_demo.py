"""Accès direct à la scène intégrée, conservé pour les commandes existantes."""

import streamlit as st

from queuesmart.config import ScenarioConfig
from queuesmart.ui.dynamic_view import render_dynamic
from queuesmart.ui.presentation import section, theme


def main() -> None:
    st.set_page_config(page_title="RetailFlow | Scène dynamique", page_icon="🛒", layout="wide")
    theme()
    section(
        "RetailFlow / Simulation dynamique",
        "Cette scène est aussi disponible dans app.py, espace Simulation.",
    )
    with st.sidebar:
        count = st.slider("Clients", 1, 500, 60)
        arrivals = st.slider("Fenêtre des arrivées (min)", 5, 120, 45)
        service = st.slider("Durée moyenne de service (min)", 0.3, 8.0, 2.0)
        seed = st.number_input("Graine aléatoire", 0, 100000, 42)
    render_dynamic(ScenarioConfig("Scène dynamique", count, arrivals, service, 3, seed=int(seed)))


if __name__ == "__main__":
    main()
