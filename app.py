"""RetailFlow, interface Streamlit simplifiée pour la simulation FIFO.

Lancer depuis la racine du projet : python -m streamlit run app.py
Le moteur dynamique et ses événements sont disponibles dans dynamic_demo.py.
"""

from __future__ import annotations

import json
from dataclasses import asdict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from queuesmart.analytics.kpi import KpiCalculator
from queuesmart.config import WAIT_THRESHOLD_MIN, ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import build_strategy
from queuesmart.ui.client_screen import render_client_screen
from queuesmart.ui.sidebar import render_sidebar
from queuesmart.ui.store_view import render_store_view

NAVY = "#14253D"
BLUE = "#4478B4"
GOLD = "#C9A45B"
GREEN = "#18826F"
PALE = "#F4F7FB"


@st.cache_data(show_spinner="Calcul du scénario...")
def run_simulation(config: ScenarioConfig, strategy_name: str) -> SimulationResult:
    """Mémoriser uniquement les entrées hashables, pas l'objet résultat."""
    return SimulationEngine(build_strategy(strategy_name)).run(config)


def customers_frame(result: SimulationResult) -> pd.DataFrame:
    """Pas de cache Streamlit : SimulationResult contient des objets non hashables."""
    return pd.DataFrame(
        {
            "Client": c.customer_id,
            "Caisse": c.register_id,
            "Arrivée": c.arrival_time,
            "Attente": c.wait_time,
            "Service": c.service_duration,
            "Début": c.service_start,
            "Sortie": c.service_end,
        }
        for c in result.customers
    )


def registers_frame(result: SimulationResult, clients: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for register in result.registers:
        part = clients.loc[clients["Caisse"] == register.register_id]
        rows.append(
            {
                "Caisse": register.register_id,
                "Clients": len(part),
                "Attente moyenne": float(part["Attente"].mean()) if len(part) else 0.0,
                "Occupation (%)": 100 * register.busy_time() / result.end_time,
            }
        )
    return pd.DataFrame(rows)


def theme() -> None:
    """Style sobre, transitions courtes et respect du mouvement réduit."""
    st.markdown(
        """
    <style>
    :root {--navy:#14253D;--gold:#C9A45B;--blue:#4478B4;--muted:#68798D;}
    .stApp {background:#F5F7FB;color:var(--navy);}
    .block-container {max-width:1740px;padding:.55rem 1.25rem 1.1rem;}
    [data-testid="stSidebar"] {background:#14253D;border-right:1px solid #2B415E;}
    [data-testid="stSidebar"] * {color:#F6F8FC;}
    [data-testid="stSidebar"] input {color:#14253D!important;}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {font-weight:550;}
    [data-testid="stSidebar"] hr {border-color:#304561;}
    h1,h2,h3 {letter-spacing:-.035em;color:var(--navy)!important;}
    h2 {font-size:1.8rem!important;margin-top:.2rem!important;}
    h3 {font-size:1.35rem!important;}
    p {line-height:1.52;}
    .rf-hero {display:flex;justify-content:space-between;align-items:center;gap:1rem;
      background:linear-gradient(115deg,#14253D,#244569);border-radius:20px;
      padding:18px 28px;color:white;margin-bottom:8px;overflow:hidden;position:relative;
      animation:rf-in .45s ease-out both;}
    .rf-hero:after {content:'';position:absolute;right:-45px;top:-100px;width:260px;height:260px;
      border-radius:50%;border:40px solid #ffffff0c;pointer-events:none;}
    .rf-eyebrow {font-size:.69rem;font-weight:750;letter-spacing:.15em;color:#E5C17D;margin-bottom:7px;}
    .rf-hero h1 {font-size:3.1rem!important;color:white!important;margin:0 0 3px!important;}
    .rf-hero p {font-size:1.12rem;color:#D4E0F0;margin:0;}
    .rf-pill {border:1px solid #ffffff35;border-radius:100px;padding:8px 13px;
      font-size:.74rem;white-space:nowrap;background:#ffffff12;z-index:1;}
    .rf-section {display:flex;align-items:baseline;justify-content:space-between;
      margin:10px 0 6px;gap:8px;}
    .rf-section strong {font-size:1.85rem;letter-spacing:-.025em;}
    .rf-section span {font-size:1.03rem;color:#6A7A8F;}
    .rf-card {background:white;border:1px solid #E5EBF2;border-radius:16px;
      padding:12px 17px;box-shadow:0 5px 20px #14253D06;animation:rf-in .45s ease-out both;}
    .rf-card .label {font-size:1.08rem;color:#69798C;margin-bottom:7px;}
    .rf-card .value {font-size:2.5rem;letter-spacing:-.045em;font-weight:750;color:#14253D;}
    .rf-card .hint {font-size:.97rem;color:#7D8A9A;margin-top:5px;}
    .rf-card:hover {border-color:#C6D6E9;transform:translateY(-2px);transition:.2s ease;}
    div[data-testid="stMetric"] {background:white;border:1px solid #E5EBF2;
      border-radius:15px;padding:15px 17px;box-shadow:0 4px 16px #14253D05;}
    [data-testid="stMetricValue"] {color:#14253D;font-weight:700;}
    [data-testid="stMetricLabel"] {color:#69798C;}
    [data-testid="stHorizontalBlock"] {align-items:stretch;gap:.75rem;}
    [data-testid="stPlotlyChart"] {background:white;border:1px solid #E7ECF3;
      border-radius:14px;padding:2px 5px;box-shadow:0 4px 16px #14253D05;}
    [data-testid="stRadio"] [role="radiogroup"] {gap:.45rem;}
    [data-testid="stRadio"] [role="radiogroup"] label {border-radius:11px;}
    [data-testid="stDownloadButton"] button {border-radius:11px;}
    div[data-testid="stTabs"] [role="tablist"] {gap:.35rem;}
    div[data-testid="stTabs"] button {border-radius:10px;padding:.65rem 1rem;}
    [data-testid="stPlotlyChart"] {transition:transform .3s ease,box-shadow .3s ease;}
    [data-testid="stPlotlyChart"]:hover {transform:translateY(-3px);box-shadow:0 12px 32px #14253D16;}
    [data-testid="stMetric"] {animation:rf-in .55s ease both;}
    [data-testid="stMetric"]:hover {transform:translateY(-3px);transition:transform .22s ease;}
    .rf-card:nth-child(2) {animation-delay:.07s;}
    .rf-card:nth-child(3) {animation-delay:.14s;}
    .rf-card:nth-child(4) {animation-delay:.21s;}
    .rf-hero {background-size:180% 180%;animation:rf-in .5s ease both,rf-glow 11s ease-in-out infinite alternate;}
    @keyframes rf-glow {0% {background-position:0% 50%}100% {background-position:100% 50%}}
    [data-testid="stTabs"] [role="tab"] {font-size:1.17rem;font-weight:700;}
    [data-testid="stRadio"] [role="radiogroup"] label {padding:.45rem .8rem!important;transition:background .2s ease;}
    [data-testid="stRadio"] [role="radiogroup"] label:hover {background:#E5EDF8;}
    [data-testid="stSidebar"] {min-width:280px;}
    .rf-foot {margin-top:22px;padding-top:15px;border-top:1px solid #E1E7F0;
      color:#8793A4;font-size:.73rem;}
    @keyframes rf-in {from {opacity:0;transform:translateY(9px)}
      to {opacity:1;transform:translateY(0)}}
    @media(max-width:800px) {.block-container {padding:1rem .8rem 2rem;}
      .rf-hero {padding:20px;}.rf-pill {display:none;}.rf-hero h1 {font-size:1.8rem!important;}}
    @media(prefers-reduced-motion:reduce) {.rf-hero,.rf-card {animation:none!important;}
      .rf-card:hover,[data-testid="stPlotlyChart"]:hover,[data-testid="stMetric"]:hover {transform:none!important;}
      .rf-hero {animation:none!important;}}
    /* Typography and density: larger content, less wasted space. */
    html {font-size:17px;}
    [data-testid="stSidebar"] {font-size:1.06rem;}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {font-size:1.06rem!important;}
    [data-testid="stSidebar"] [data-testid="stSlider"] {margin-bottom:-.45rem;}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap:.45rem;}
    [data-testid="stVerticalBlock"] {gap:.55rem;}
    [data-testid="stPlotlyChart"] {animation:rf-rise .58s cubic-bezier(.2,.8,.2,1) both;}
    [data-testid="stPlotlyChart"]:nth-of-type(even) {animation-delay:.1s;}
    [data-testid="stPlotlyChart"] .modebar {opacity:0;transition:opacity .2s;}
    [data-testid="stPlotlyChart"]:hover .modebar {opacity:1;}
    .rf-hero:before {content:'';position:absolute;inset:-60% auto -60% -35%;width:25%;
      transform:rotate(20deg) translateX(-200%);background:linear-gradient(90deg,transparent,#ffffff16,transparent);
      animation:rf-sheen 9s ease-in-out infinite;pointer-events:none;}
    .rf-hero:after {animation:rf-orbit 12s ease-in-out infinite alternate;}
    .rf-pill {animation:rf-breathe 4s ease-in-out infinite;}
    .rf-card {transition:transform .24s ease,box-shadow .24s ease,border-color .24s ease;}
    .rf-card:hover {box-shadow:0 14px 28px #14253D18;}
    [data-testid="stRadio"] [role="radiogroup"] label {font-size:1.1rem!important;}
    [data-testid="stTabs"] button {font-size:1.12rem!important;}
    [data-testid="stPlotlyChart"] svg text {font-size:15px;}
    @keyframes rf-rise {from {opacity:0;transform:translateY(18px) scale(.99)}to {opacity:1;transform:translateY(0) scale(1)}}
    @keyframes rf-sheen {0%,68% {transform:rotate(20deg) translateX(-300%)}88%,100% {transform:rotate(20deg) translateX(1100%)}}
    @keyframes rf-orbit {from {transform:translate(-12px,4px) scale(.95)}to {transform:translate(12px,-8px) scale(1.07)}}
    @keyframes rf-breathe {0%,100% {box-shadow:0 0 0 0 #d7b36e00}50% {box-shadow:0 0 0 6px #d7b36e12}}
    @media(prefers-reduced-motion:reduce) {
      *,*::before,*::after {animation:none!important;transition:none!important;scroll-behavior:auto!important;}
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def hero(config: ScenarioConfig) -> None:
    st.markdown(
        f"""
    <div class="rf-hero">
      <div><div class="rf-eyebrow">SIMULATION ET OPTIMISATION</div>
      <h1>RetailFlow<span style="color:#D7B36E">.</span></h1>
      <p>Comprendre les files d'attente. Tester les décisions. Améliorer le service.</p></div>
      <div class="rf-pill">{config.name} &nbsp; | &nbsp; Simulation FIFO</div>
    </div>""",
        unsafe_allow_html=True,
    )


def section(title: str, caption: str = "") -> None:
    st.markdown(
        f'<div class="rf-section"><strong>{title}</strong><span>{caption}</span></div>',
        unsafe_allow_html=True,
    )


def chart(fig: go.Figure, height: int = 320) -> None:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=42, b=22),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color=NAVY, size=17),
        title_font=dict(size=20),
        legend=dict(orientation="h", y=1.16, x=0),
        hoverlabel=dict(bgcolor="white"),
        transition=dict(duration=550, easing="cubic-in-out"),
    )
    fig.update_traces(
        selector=dict(type="scatter"), marker=dict(line=dict(width=0.6, color="#FFFFFF"))
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False, tickfont=dict(size=15), title_font=dict(size=17)
    )
    fig.update_yaxes(
        gridcolor="#EAF0F6", zeroline=False, tickfont=dict(size=15), title_font=dict(size=17)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def kpis(result: SimulationResult) -> None:
    report = KpiCalculator().compute(result)
    cards = [
        ("Clients simulés", str(report.customer_count), "Parcours terminés"),
        ("Attente moyenne", f"{report.mean_wait:.1f} min", "Avant le passage en caisse"),
        ("Attente P90", f"{report.p90_wait:.1f} min", "90 % des attentes sous ce seuil"),
        (
            "Service sous 5 min",
            f"{100 * (1 - report.share_over_threshold):.0f} %",
            "Part des clients",
        ),
    ]
    for column, (label, value, hint) in zip(st.columns(4), cards):
        with column:
            st.markdown(
                f'<div class="rf-card"><div class="label">{label}</div>'
                f'<div class="value">{value}</div><div class="hint">{hint}</div></div>',
                unsafe_allow_html=True,
            )


def overview(config: ScenarioConfig, result: SimulationResult, clients: pd.DataFrame) -> None:
    section("Vue d'ensemble", "Les chiffres essentiels, sans surcharge")
    kpis(result)
    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        section("Temps d'attente")
        fig = px.histogram(
            clients,
            x="Attente",
            nbins=22,
            title="Distribution des attentes",
            color_discrete_sequence=[BLUE],
        )
        fig.add_vline(
            x=WAIT_THRESHOLD_MIN,
            line_color=GOLD,
            line_dash="dash",
            annotation_text="Objectif 5 min",
            annotation_position="top right",
        )
        fig.update_layout(xaxis_title="Minutes", yaxis_title="Clients", showlegend=False)
        chart(fig)
    with right:
        section("Lecture rapide")
        report = KpiCalculator().compute(result)
        if report.share_over_threshold <= 0.10:
            st.success(
                "Objectif de service atteint : au moins 90 % des clients attendent 5 min ou moins."
            )
        else:
            st.warning("Objectif non atteint : plus de 10 % des clients attendent plus de 5 min.")
        st.metric("Occupation moyenne", f"{100 * report.mean_utilization:.0f} %")
        st.caption(
            f"{config.open_registers} caisses ouvertes. Durée totale simulée : {result.end_time:.1f} min."
        )
        st.caption("Données synthétiques, résultats dépendants du scénario.")
    section("Arrivées et congestion", "Chaque point représente un client simulé")
    scatter = px.scatter(
        clients,
        x="Arrivée",
        y="Attente",
        color="Caisse",
        size="Service",
        hover_data=["Client", "Début", "Sortie"],
        title="Nuage de points : arrivée et attente par client",
        color_continuous_scale=[[0, "#85B8D9"], [0.5, BLUE], [1, NAVY]],
        opacity=0.8,
    )
    scatter.add_hline(
        y=WAIT_THRESHOLD_MIN, line_color=GOLD, line_dash="dash", annotation_text="Seuil 5 min"
    )
    scatter.update_layout(xaxis_title="Minute d'arrivée", yaxis_title="Attente (min)")
    chart(scatter, 390)
    section("Activité des caisses", "Charge et répartition des clients")
    registers = registers_frame(result, clients)
    fig = px.bar(
        registers,
        x="Caisse",
        y="Clients",
        title="Clients servis par caisse",
        color_discrete_sequence=[BLUE],
        text="Clients",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis=dict(dtick=1))
    chart(fig, 300)
    left, right = st.columns(2, gap="large")
    with left:
        timeline = px.scatter(
            clients,
            x="Début",
            y="Caisse",
            color="Attente",
            size="Service",
            hover_data=["Client", "Arrivée", "Sortie"],
            color_continuous_scale="Blues",
            title="Chronologie des passages en caisse",
        )
        timeline.update_layout(
            xaxis_title="Minute de début de service", yaxis_title="Caisse", yaxis=dict(dtick=1)
        )
        chart(timeline, 315)
    with right:
        arrival = clients.copy()
        arrival["Tranche (10 min)"] = (arrival["Arrivée"] // 10 * 10).astype(int)
        grouped = arrival.groupby("Tranche (10 min)", as_index=False).agg(
            Clients=("Client", "count"), Attente=("Attente", "mean")
        )
        bars = px.bar(
            grouped,
            x="Tranche (10 min)",
            y="Clients",
            title="Affluence par tranche de 10 minutes",
            color_discrete_sequence=[BLUE],
            text="Clients",
        )
        bars.update_layout(xaxis_title="Début de tranche (min)", yaxis_title="Clients")
        chart(bars, 315)


def simulation(result: SimulationResult) -> None:
    section("Magasin en simulation", "Déplace le temps pour explorer l'activité")
    st.caption(
        "Vue schématique du moteur FIFO. La scène pixel art animée sera intégrée séparément."
    )
    tab_scene, tab_client = st.tabs(["Magasin", "Écran client"])
    with tab_scene:
        render_store_view(result)
    with tab_client:
        render_client_screen(result)


def analytics(result: SimulationResult, clients: pd.DataFrame) -> None:
    section("Analyse des performances", "Distributions, corrélations et performance des caisses")
    tab_wait, tab_register, tab_customers = st.tabs(["Attentes", "Caisses", "Clients"])
    with tab_wait:
        left, right = st.columns(2)
        with left:
            fig = px.box(
                clients,
                x="Caisse",
                y="Attente",
                title="Dispersion des attentes",
                color_discrete_sequence=[BLUE],
            )
            fig.update_layout(xaxis=dict(dtick=1))
            chart(fig)
        with right:
            fig = px.scatter(
                clients,
                x="Arrivée",
                y="Attente",
                color="Caisse",
                title="Attente selon l'heure d'arrivée",
                opacity=0.7,
                color_continuous_scale="Blues",
            )
            chart(fig)
        left, right = st.columns(2, gap="large")
        with left:
            fig = px.histogram(
                clients,
                x="Attente",
                nbins=28,
                title="Histogramme détaillé des temps d'attente",
                color_discrete_sequence=[BLUE],
            )
            fig.add_vline(x=WAIT_THRESHOLD_MIN, line_color=GOLD, line_dash="dash")
            fig.update_layout(xaxis_title="Attente (min)", yaxis_title="Clients")
            chart(fig)
        with right:
            fig = px.scatter(
                clients,
                x="Service",
                y="Attente",
                color="Caisse",
                size="Service",
                opacity=0.75,
                title="Nuage de points : durée de service et attente",
                color_continuous_scale="Blues",
            )
            fig.update_layout(xaxis_title="Durée du service (min)", yaxis_title="Attente (min)")
            chart(fig)
    with tab_register:
        frame = registers_frame(result, clients)
        fig = px.bar(
            frame,
            x="Caisse",
            y="Occupation (%)",
            title="Occupation des caisses",
            color_discrete_sequence=[GOLD],
        )
        fig.update_layout(xaxis=dict(dtick=1))
        chart(fig)
        a, b = st.columns(2, gap="large")
        with a:
            fig = px.bar(
                frame,
                x="Caisse",
                y="Attente moyenne",
                title="Attente moyenne par caisse",
                color_discrete_sequence=[BLUE],
            )
            fig.update_layout(xaxis=dict(dtick=1))
            chart(fig, 300)
        with b:
            fig = px.scatter(
                frame,
                x="Occupation (%)",
                y="Attente moyenne",
                size="Clients",
                text="Caisse",
                title="Occupation et attente par caisse",
                color_discrete_sequence=[GOLD],
            )
            fig.update_traces(textposition="top center")
            chart(fig, 300)
        st.dataframe(frame.round(2), hide_index=True, use_container_width=True)
    with tab_customers:
        selected = st.selectbox("Client à examiner", clients["Client"].tolist())
        customer = clients.loc[clients["Client"] == selected].iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Caisse", int(customer["Caisse"]))
        c2.metric("Attente", f"{customer['Attente']:.1f} min")
        c3.metric("Passage", f"{customer['Service']:.1f} min")
        with st.expander("Afficher toutes les données clients"):
            st.dataframe(clients.round(2), hide_index=True, use_container_width=True)


def comparison(
    config: ScenarioConfig, strategy_name: str, result: SimulationResult, clients: pd.DataFrame
) -> None:
    section("Tester une décision", "Comparer plusieurs capacités sur un scénario identique")
    st.caption(
        "Les simulations utilisent la même graine. Les résultats ne constituent pas une prévision réelle."
    )
    maximum = st.slider("Nombre maximal de caisses à comparer", 2, 8, 5)
    if st.button("Comparer les configurations", type="primary", use_container_width=True):
        st.session_state["rf_compare_request"] = (config, strategy_name, maximum)
    request = st.session_state.get("rf_compare_request")
    if request is not None:
        old_config, old_strategy, old_maximum = request
        if old_config != config or old_strategy != strategy_name or old_maximum != maximum:
            st.info("Les paramètres ont changé. Relance la comparaison.")
        else:
            rows = []
            with st.spinner("Comparaison des capacités..."):
                for n in range(1, maximum + 1):
                    simulated = run_simulation(config.with_registers(n), strategy_name)
                    report = KpiCalculator().compute(simulated)
                    rows.append(
                        {
                            "Caisses": n,
                            "Attente moyenne": report.mean_wait,
                            "P90": report.p90_wait,
                            "Part sous 5 min (%)": 100 * (1 - report.share_over_threshold),
                        }
                    )
            frame = pd.DataFrame(rows)
            fig = px.line(
                frame,
                x="Caisses",
                y=["Attente moyenne", "P90"],
                markers=True,
                title="Effet du nombre de caisses sur l'attente",
            )
            fig.update_layout(xaxis=dict(dtick=1), yaxis_title="Minutes")
            chart(fig, 340)
            st.dataframe(frame.round(2), hide_index=True, use_container_width=True)
            candidates = frame.loc[frame["Part sous 5 min (%)"] >= 90]
            if len(candidates):
                st.success(
                    f"Plus petite capacité respectant l'objectif dans ce test : {int(candidates.iloc[0]['Caisses'])} caisses."
                )
            else:
                st.warning("Aucune configuration testée n'atteint 90 % de clients sous 5 minutes.")
    section("Télécharger les résultats", "CSV compatible avec Excel")
    csv = clients.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    col1, col2 = st.columns(2)
    col1.download_button(
        "Exporter les clients (CSV)",
        csv,
        "retailflow_clients.csv",
        "text/csv",
        use_container_width=True,
    )
    config_json = json.dumps(
        {"configuration": asdict(config), "strategie": strategy_name}, ensure_ascii=False, indent=2
    )
    col2.download_button(
        "Exporter les paramètres (JSON)",
        config_json,
        "retailflow_parametres.json",
        "application/json",
        use_container_width=True,
    )
    with st.expander("Méthode et limites"):
        st.write("Simulation historique FIFO, avec données synthétiques et graine reproductible.")
        st.write("Le temps d'attente est le délai entre arrivée et début de service.")
        st.write("Le P90 correspond au 90e percentile empirique des temps d'attente.")
        st.write(
            "Les changements de file, abandons et ouvertures dynamiques relèvent du moteur séparé."
        )


def main() -> None:
    st.set_page_config(
        page_title="RetailFlow | Simulateur",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    theme()
    config, strategy_name = render_sidebar()
    result = run_simulation(config, strategy_name)
    hero(config)
    pages = ["Vue d'ensemble", "Simulation", "Analyse", "Comparaison"]
    page = st.radio("Navigation", pages, horizontal=True, label_visibility="collapsed")
    if page == "Vue d'ensemble":
        overview(config, result, customers_frame(result))
    elif page == "Simulation":
        simulation(result)
    elif page == "Analyse":
        analytics(result, customers_frame(result))
    else:
        comparison(config, strategy_name, result, customers_frame(result))
    st.markdown(
        '<div class="rf-foot">RetailFlow | Simulation pédagogique FIFO | Données synthétiques</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
