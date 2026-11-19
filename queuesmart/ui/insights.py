"""RetailFlow Studio: explorations analytiques complémentaires.

Le module est volontairement séparé du moteur: aucune mutation des résultats.
Toutes les valeurs présentées proviennent du SimulationResult ou de calculs
explicites sur ses clients. Les simulations alternatives sont isolées.
"""

from __future__ import annotations

import io
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from queuesmart.analytics.kpi import KpiCalculator
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.result import SimulationResult
from queuesmart.simulation.strategies import build_strategy

NAVY = '#14233b'
BLUE = '#2862a4'
GOLD = '#d6a858'
TEAL = '#168c89'
RED = '#cf6470'
GRAY = '#708198'
PALETTE = [BLUE, GOLD, TEAL, RED, '#8976b7', '#73a6ce', '#b8a15c', '#638a78']
WAIT_TARGET = 5.0


@dataclass(frozen=True)
class StudioSummary:
    customers: int
    registers: int
    mean_wait: float
    median_wait: float
    p90_wait: float
    maximum_wait: float
    mean_service: float
    total_service: float
    duration: float
    throughput: float
    service_level: float
    total_wait: float
    worst_register: int | None
    best_register: int | None


def _minutes(value: float) -> str:
    if not math.isfinite(value):
        return 'N/A'
    return f'{value:.1f} min'


def _percentage(value: float) -> str:
    return f'{100 * value:.1f} %'


def _number(value: float) -> str:
    return f'{value:,.1f}'.replace(',', ' ')


def _safe_mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _safe_percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _plot_style(fig: go.Figure, title: str = '', height: int = 360) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=17, color=NAVY)),
        font=dict(family='Arial, sans-serif', color=NAVY, size=12),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=16, r=16, t=55, b=22),
        colorway=PALETTE,
        hoverlabel=dict(bgcolor='white', font_color=NAVY),
        legend=dict(orientation='h', y=-0.2),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor='#dce5ef')
    fig.update_yaxes(showgrid=True, gridcolor='#e8edf4', zeroline=False)
    return fig


def _heading(title: str, description: str) -> None:
    st.markdown(f'### {title}')
    st.caption(description)


def _callout(title: str, text: str, tone: str = 'blue') -> None:
    border = {'blue': BLUE, 'gold': GOLD, 'red': RED, 'teal': TEAL}.get(tone, BLUE)
    st.markdown(
        '<div style="padding:15px 18px;background:#fff;border:1px solid #e0e7f0;'
        f'border-left:4px solid {border};border-radius:12px;margin:12px 0">'
        f'<strong style="color:{NAVY}">{escape(title)}</strong>'
        f'<p style="color:#52677d;margin:7px 0 0">{escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def customer_frame(result: SimulationResult) -> pd.DataFrame:
    """Une ligne par client, temps en minutes depuis t=0."""
    return pd.DataFrame([
        {
            'client': c.customer_id,
            'arrivee_min': c.arrival_time,
            'caisse': c.register_id,
            'debut_service_min': c.service_start,
            'fin_service_min': c.service_end,
            'attente_min': c.wait_time,
            'service_min': c.service_duration,
            'temps_systeme_min': c.service_end - c.arrival_time,
            'attente_longue': c.wait_time > WAIT_TARGET,
        }
        for c in result.customers
    ])


def register_frame(result: SimulationResult) -> pd.DataFrame:
    grouped: dict[int, list[Any]] = defaultdict(list)
    for c in result.customers:
        grouped[int(c.register_id)].append(c)
    rows = []
    for reg in result.registers:
        customers = grouped[reg.register_id]
        waits = [c.wait_time for c in customers]
        busy = sum(c.service_duration for c in customers)
        rows.append({
            'caisse': reg.register_id,
            'clients': len(customers),
            'attente_moy_min': _safe_mean(waits),
            'attente_p90_min': _safe_percentile(waits, .9),
            'attente_max_min': max(waits, default=0),
            'service_total_min': busy,
            'occupation_pct': 100 * busy / result.end_time if result.end_time else 0,
            'part_attente_longue_pct': 100 * sum(w > WAIT_TARGET for w in waits) / len(waits) if waits else 0,
        })
    return pd.DataFrame(rows)


def summary(result: SimulationResult) -> StudioSummary:
    customers = customer_frame(result)
    registers = register_frame(result)
    waits = customers['attente_min'].tolist()
    services = customers['service_min'].tolist()
    mean_by_reg = registers.set_index('caisse')['attente_moy_min']
    return StudioSummary(
        customers=len(customers),
        registers=len(registers),
        mean_wait=_safe_mean(waits),
        median_wait=statistics.median(waits),
        p90_wait=_safe_percentile(waits, .9),
        maximum_wait=max(waits),
        mean_service=_safe_mean(services),
        total_service=sum(services),
        duration=result.end_time,
        throughput=60 * len(customers) / result.end_time if result.end_time else 0,
        service_level=sum(w <= WAIT_TARGET for w in waits) / len(waits),
        total_wait=sum(waits),
        worst_register=int(mean_by_reg.idxmax()) if not mean_by_reg.empty else None,
        best_register=int(mean_by_reg.idxmin()) if not mean_by_reg.empty else None,
    )


def timeline_frame(result: SimulationResult, step: float = 1.0) -> pd.DataFrame:
    """Reconstruit les états à pas constant, sans modifier le moteur."""
    if step <= 0:
        raise ValueError('Le pas temporel doit être positif.')
    rows = []
    count = math.ceil(result.end_time / step)
    for index in range(count + 1):
        t = min(index * step, result.end_time)
        snapshot = result.snapshot_at(t)
        waiting = sum(len(r.waiting_customer_ids) for r in snapshot.registers)
        serving = sum(r.serving_customer_id is not None for r in snapshot.registers)
        rows.append({
            'minute': t,
            'en_attente': waiting,
            'en_service': serving,
            'presents': waiting + serving,
            'non_arrives': snapshot.not_arrived_count,
            'sortis': snapshot.departed_count,
            'files_actives': sum(r.queue_length > 0 for r in snapshot.registers),
            'file_max': max((r.queue_length for r in snapshot.registers), default=0),
        })
    return pd.DataFrame(rows)


def event_frame(result: SimulationResult) -> pd.DataFrame:
    rows = []
    for customer in result.customers:
        rows.extend([
            {'minute': customer.arrival_time, 'evenement': 'Arrivée', 'client': customer.customer_id, 'caisse': customer.register_id},
            {'minute': customer.service_start, 'evenement': 'Début de service', 'client': customer.customer_id, 'caisse': customer.register_id},
            {'minute': customer.service_end, 'evenement': 'Départ', 'client': customer.customer_id, 'caisse': customer.register_id},
        ])
    return pd.DataFrame(rows).sort_values(['minute', 'client', 'evenement']).reset_index(drop=True)


def arrival_frame(result: SimulationResult, bucket: int = 5) -> pd.DataFrame:
    df = customer_frame(result)
    df['periode'] = (df['arrivee_min'] // bucket).astype(int) * bucket
    agg = df.groupby('periode', as_index=False).agg(
        arrivees=('client', 'count'),
        attente_moy_min=('attente_min', 'mean'),
        attente_max_min=('attente_min', 'max'),
        service_moy_min=('service_min', 'mean'),
    )
    return agg


def service_distribution(result: SimulationResult) -> pd.DataFrame:
    df = customer_frame(result)
    boundaries = [0, 1, 2, 3, 5, 10, math.inf]
    labels = ['< 1 min', '1-2 min', '2-3 min', '3-5 min', '5-10 min', '10+ min']
    df['classe'] = pd.cut(df['service_min'], bins=boundaries, labels=labels, right=False)
    return df.groupby('classe', observed=False).size().rename('clients').reset_index()


def wait_distribution(result: SimulationResult) -> pd.DataFrame:
    df = customer_frame(result)
    boundaries = [0, 1, 2, 3, 5, 10, 15, 30, math.inf]
    labels = ['< 1', '1-2', '2-3', '3-5', '5-10', '10-15', '15-30', '30+']
    df['classe'] = pd.cut(df['attente_min'], bins=boundaries, labels=labels, right=False)
    return df.groupby('classe', observed=False).size().rename('clients').reset_index()


def fairness_frame(result: SimulationResult) -> pd.DataFrame:
    df = customer_frame(result).sort_values('arrivee_min').copy()
    df['quartile_arrivee'] = pd.qcut(df['arrivee_min'].rank(method='first'), 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
    return df.groupby('quartile_arrivee', observed=False).agg(
        clients=('client', 'count'),
        attente_moy_min=('attente_min', 'mean'),
        attente_p90_min=('attente_min', lambda values: _safe_percentile(values.tolist(), .9)),
        attente_longue_pct=('attente_longue', lambda values: 100 * values.mean()),
    ).reset_index()


def _chart_line(df: pd.DataFrame, x: str, ys: list[str], title: str, labels: dict[str, str] | None = None) -> go.Figure:
    fig = go.Figure()
    for idx, name in enumerate(ys):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[name], mode='lines', name=(labels or {}).get(name, name),
            line=dict(color=PALETTE[idx % len(PALETTE)], width=2.8),
            hovertemplate='%{x:.1f} min<br>%{y:.1f}<extra>%{fullData.name}</extra>',
        ))
    return _plot_style(fig, title)


def _chart_bar(df: pd.DataFrame, x: str, y: str, title: str, color: str = BLUE) -> go.Figure:
    fig = px.bar(df, x=x, y=y, color_discrete_sequence=[color], text_auto='.1f')
    fig.update_traces(textposition='outside', cliponaxis=False)
    return _plot_style(fig, title)


def _chart_hist(df: pd.DataFrame, column: str, title: str, bins: int = 22) -> go.Figure:
    fig = px.histogram(df, x=column, nbins=bins, color_discrete_sequence=[BLUE])
    fig.update_traces(marker_line_color='white', marker_line_width=.8)
    return _plot_style(fig, title)


def _chart_scatter(df: pd.DataFrame, title: str) -> go.Figure:
    fig = px.scatter(
        df, x='arrivee_min', y='attente_min', color='caisse',
        hover_data=['client', 'service_min'], color_continuous_scale='Blues',
        opacity=.75,
    )
    fig.add_hline(y=WAIT_TARGET, line_dash='dash', line_color=RED,
                  annotation_text='Seuil 5 min', annotation_position='top left')
    return _plot_style(fig, title)


def _chart_gauge(value: float, target: float, title: str, suffix: str = ' min') -> go.Figure:
    ceiling = max(target * 2, value * 1.2, 1)
    fig = go.Figure(go.Indicator(
        mode='gauge+number', value=value,
        number={'suffix': suffix, 'font': {'size': 34, 'color': NAVY}},
        gauge={
            'axis': {'range': [0, ceiling]},
            'bar': {'color': BLUE},
            'bgcolor': '#e9eff6',
            'steps': [{'range': [0, target], 'color': '#d9f0e9'}],
            'threshold': {'line': {'color': RED, 'width': 4}, 'value': target},
        },
    ))
    return _plot_style(fig, title, height=290)


def _metric_grid(s: StudioSummary) -> None:
    first = st.columns(4)
    first[0].metric('Clients simulés', f'{s.customers:,}')
    first[1].metric('Caisses', s.registers)
    first[2].metric('Attente moyenne', _minutes(s.mean_wait))
    first[3].metric('Attente P90', _minutes(s.p90_wait))
    second = st.columns(4)
    second[0].metric('Niveau de service ≤ 5 min', _percentage(s.service_level))
    second[1].metric('Débit estimé', f'{s.throughput:.1f} clients/h')
    second[2].metric('Temps de simulation', _minutes(s.duration))
    second[3].metric('Attente cumulée', _minutes(s.total_wait))


def render_overview(result: SimulationResult) -> None:
    """Synthèse, qualité de service et charge du système."""
    s = summary(result)
    _heading('Vue exécutive', 'Indicateurs calculés sur les clients de la simulation sélectionnée.')
    _metric_grid(s)
    left, right = st.columns([1.2, 1])
    with left:
        frame = timeline_frame(result, max(1, result.end_time / 150))
        st.plotly_chart(
            _chart_line(frame, 'minute', ['en_attente', 'en_service'],
                        'Évolution de la présence aux caisses',
                        {'en_attente': 'En attente', 'en_service': 'En service'}),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(_chart_gauge(s.mean_wait, WAIT_TARGET, 'Attente moyenne vs seuil'), use_container_width=True)
    if s.mean_wait > WAIT_TARGET:
        _callout('Vigilance sur le délai moyen',
                 'L’attente moyenne dépasse 5 minutes. Tester des caisses supplémentaires ou une répartition différente.', 'red')
    else:
        _callout('Attente moyenne sous le seuil',
                 'La moyenne respecte 5 minutes, mais il faut aussi examiner les valeurs extrêmes et le P90.', 'teal')
    st.caption('Le seuil de 5 minutes est une convention analytique, pas une norme réglementaire.')


def render_waits(result: SimulationResult) -> None:
    """Distribution, percentiles et équité entre groupes de clients."""
    df = customer_frame(result)
    _heading('Analyse des temps d’attente', 'Distribution, dispersion et exposition aux attentes longues.')
    p10 = _safe_percentile(df['attente_min'].tolist(), .1)
    p25 = _safe_percentile(df['attente_min'].tolist(), .25)
    p75 = _safe_percentile(df['attente_min'].tolist(), .75)
    p95 = _safe_percentile(df['attente_min'].tolist(), .95)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('P10', _minutes(p10))
    c2.metric('P25', _minutes(p25))
    c3.metric('P75', _minutes(p75))
    c4.metric('P95', _minutes(p95))
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_chart_hist(df, 'attente_min', 'Distribution des attentes'), use_container_width=True)
    with right:
        grouped = wait_distribution(result)
        st.plotly_chart(_chart_bar(grouped, 'classe', 'clients', 'Clients par tranche d’attente', GOLD), use_container_width=True)
    st.plotly_chart(_chart_scatter(df, 'Attente selon la minute d’arrivée'), use_container_width=True)
    st.markdown('#### Équité entre périodes d’arrivée')
    equity = fairness_frame(result)
    st.dataframe(equity, use_container_width=True, hide_index=True)
    st.caption('Les quartiles découpent les clients par ordre d’arrivée, pas en tranches de durée identique.')
    st.plotly_chart(_chart_bar(equity, 'quartile_arrivee', 'attente_moy_min',
                              'Attente moyenne par quartile d’arrivée', TEAL), use_container_width=True)


def render_registers(result: SimulationResult) -> None:
    """Comparaison des performances et de l’occupation des caisses."""
    df = register_frame(result)
    _heading('Performance des caisses', 'Comparer charge, débit et temps d’attente par poste.')
    st.dataframe(df, use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    with a:
        st.plotly_chart(_chart_bar(df, 'caisse', 'clients', 'Clients traités par caisse'), use_container_width=True)
        st.plotly_chart(_chart_bar(df, 'caisse', 'attente_moy_min', 'Attente moyenne par caisse', GOLD), use_container_width=True)
    with b:
        st.plotly_chart(_chart_bar(df, 'caisse', 'occupation_pct', 'Occupation des caisses (%)', TEAL), use_container_width=True)
        st.plotly_chart(_chart_bar(df, 'caisse', 'attente_p90_min', 'P90 d’attente par caisse', RED), use_container_width=True)
    if len(df) > 1:
        spread = df['attente_moy_min'].max() - df['attente_moy_min'].min()
        _callout('Écart de répartition',
                 f'Écart de {spread:.1f} minute(s) entre la caisse la plus rapide et la plus lente en attente moyenne. '
                 'Ce constat ne prouve pas une causalité : les heures d’arrivée et la durée des services diffèrent.')
    st.caption('Occupation = durée totale de service / durée totale de la simulation. Les caisses restent ouvertes pendant toute la simulation historique.')


def render_flow(result: SimulationResult) -> None:
    """Chronologie des événements et dynamique de congestion."""
    _heading('Flux et chronologie', 'Observer la formation et la résorption des files.')
    step = st.select_slider('Résolution temporelle', options=[.5, 1., 2., 5., 10.], value=2., format_func=lambda x: f'{x:g} min', key='rf_flow_step')
    timeline = timeline_frame(result, step)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_chart_line(timeline, 'minute', ['presents', 'en_attente'],
                                   'Clients présents aux caisses'), use_container_width=True)
    with right:
        st.plotly_chart(_chart_line(timeline, 'minute', ['non_arrives', 'sortis'],
                                   'Clients non arrivés et clients partis'), use_container_width=True)
    st.plotly_chart(_chart_line(timeline, 'minute', ['file_max', 'files_actives'],
                               'Taille maximale d’une file et files actives'), use_container_width=True)
    with st.expander('Consulter les événements élémentaires'):
        events = event_frame(result)
        event_type = st.multiselect('Types d’événements', sorted(events['evenement'].unique()), default=sorted(events['evenement'].unique()), key='rf_event_filter')
        filtered = events[events['evenement'].isin(event_type)]
        st.dataframe(filtered, use_container_width=True, hide_index=True, height=350)
        _csv_button('Télécharger les événements', filtered, 'retailflow_evenements.csv', 'rf_events_csv')
    st.caption('Chronologie reconstruite depuis les heures de service. Les changements de file et abandons appartiennent au moteur dynamique séparé.')


def render_customer_explorer(result: SimulationResult) -> None:
    """Explorateur des trajectoires et recherche multicritère."""
    _heading('Explorateur clients', 'Rechercher les situations atypiques et inspecter les parcours.')
    df = customer_frame(result)
    a, b, c = st.columns([1.1, 1, 1])
    with a:
        registers = st.multiselect('Caisses', sorted(df['caisse'].unique()), default=sorted(df['caisse'].unique()), key='rf_customer_registers')
    with b:
        wait_min = st.number_input('Attente minimale (min)', min_value=0., max_value=float(math.ceil(df['attente_min'].max()) + 1), value=0., step=.5, key='rf_customer_wait_min')
    with c:
        long_only = st.checkbox('Uniquement attentes > 5 min', key='rf_customer_long')
    filtered = df[df['caisse'].isin(registers) & (df['attente_min'] >= wait_min)]
    if long_only:
        filtered = filtered[filtered['attente_longue']]
    st.caption(f'{len(filtered)} client(s) sur {len(df)} correspondent aux filtres.')
    st.dataframe(filtered.sort_values('attente_min', ascending=False), use_container_width=True, hide_index=True, height=340)
    _csv_button('Exporter la sélection', filtered, 'retailflow_clients_filtres.csv', 'rf_customer_export')
    st.markdown('#### Parcours individuel')
    client_id = st.selectbox('Identifiant du client', df['client'].tolist(), key='rf_customer_id')
    client = result.customer(int(client_id))
    a, b, c, d = st.columns(4)
    a.metric('Arrivée', _minutes(client.arrival_time))
    b.metric('Début de service', _minutes(client.service_start))
    c.metric('Attente', _minutes(client.wait_time))
    d.metric('Départ', _minutes(client.service_end))
    st.caption(f'Caisse {client.register_id}, durée de service {client.service_duration:.2f} min.')
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Attente', x=[client.wait_time], y=['Client'], orientation='h', marker_color=GOLD))
    fig.add_trace(go.Bar(name='Service', x=[client.service_duration], y=['Client'], orientation='h', marker_color=BLUE))
    fig.update_layout(barmode='stack', xaxis_title='Durée (minutes)')
    st.plotly_chart(_plot_style(fig, 'Décomposition du passage en caisse', 220), use_container_width=True)


def render_arrivals(result: SimulationResult) -> None:
    """Analyse des vagues d’arrivée et des services."""
    _heading('Arrivées et demande', 'Repérer les pics de demande et leurs effets sur les délais.')
    bucket = st.select_slider('Regroupement des arrivées', options=[1, 2, 5, 10, 15, 30], value=5, format_func=lambda x: f'{x} min', key='rf_arrival_bucket')
    df = arrival_frame(result, bucket)
    a, b = st.columns(2)
    with a:
        st.plotly_chart(_chart_bar(df, 'periode', 'arrivees', 'Arrivées par intervalle'), use_container_width=True)
    with b:
        st.plotly_chart(_chart_line(df, 'periode', ['attente_moy_min'],
                                   'Attente moyenne des arrivants'), use_container_width=True)
    service = service_distribution(result)
    st.plotly_chart(_chart_bar(service, 'classe', 'clients', 'Durée des services par tranche', TEAL), use_container_width=True)
    if not df.empty:
        peak = df.loc[df['arrivees'].idxmax()]
        _callout('Période la plus chargée',
                 f'{int(peak["arrivees"])} arrivée(s) entre t={peak["periode"]:.0f} et t={peak["periode"] + bucket:.0f} minutes. '
                 'Il s’agit d’un résultat de la graine sélectionnée, pas d’une prévision réelle.')


def _run_variant(config: ScenarioConfig, strategy: str, registers: int) -> SimulationResult:
    return SimulationEngine(build_strategy(strategy)).run(config.with_registers(registers))


@st.cache_data(show_spinner='Comparaison des configurations…')
def compare_registers(config: ScenarioConfig, strategy: str, maximum: int = 8) -> pd.DataFrame:
    """Comparaison à graine identique, chaque scénario recalculé indépendamment."""
    rows = []
    for n in range(1, maximum + 1):
        result = _run_variant(config, strategy, n)
        kpi = KpiCalculator().compute(result)
        rows.append({
            'caisses': n,
            'attente_moy_min': kpi.mean_wait,
            'attente_p90_min': kpi.p90_wait,
            'attente_max_min': kpi.max_wait,
            'part_longue_pct': 100 * kpi.share_over_threshold,
            'occupation_pct': 100 * kpi.mean_utilization,
            'duree_min': result.end_time,
            'clients': kpi.customer_count,
        })
    return pd.DataFrame(rows)


def render_scenarios(config: ScenarioConfig, strategy: str) -> None:
    """Analyse de sensibilité au nombre de caisses."""
    _heading('Laboratoire de scénarios', 'Évaluer les compromis entre capacité et qualité de service.')
    _callout('Comparaison contrôlée',
             'Chaque configuration utilise les mêmes paramètres et la même graine. '
             'Les résultats illustrent un scénario simulé et ne constituent pas une garantie statistique.')
    max_registers = st.slider('Nombre maximal de caisses à comparer', 2, 8, 5, key='rf_scenario_max')
    df = compare_registers(config, strategy, max_registers)
    a, b = st.columns(2)
    with a:
        st.plotly_chart(_chart_line(df.rename(columns={'caisses': 'minute'}), 'minute',
                                   ['attente_moy_min', 'attente_p90_min'],
                                   'Attente selon le nombre de caisses',
                                   {'attente_moy_min': 'Moyenne', 'attente_p90_min': 'P90'}), use_container_width=True)
    with b:
        st.plotly_chart(_chart_bar(df, 'caisses', 'occupation_pct', 'Occupation moyenne (%)', TEAL), use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    target = st.slider('Objectif d’attente moyenne (min)', .5, 20., 5., .5, key='rf_scenario_target')
    feasible = df[df['attente_moy_min'] <= target]
    if not feasible.empty:
        winner = feasible.iloc[0]
        _callout('Configuration minimale observée',
                 f'{int(winner["caisses"])} caisse(s) suffisent pour obtenir une attente moyenne de '
                 f'{winner["attente_moy_min"]:.2f} min sur cette graine. '
                 'Une validation sur plusieurs graines est nécessaire avant toute recommandation opérationnelle.', 'teal')
    else:
        _callout('Objectif non atteint',
                 f'Aucune configuration testée de 1 à {max_registers} caisses ne respecte la cible.', 'red')
    _csv_button('Exporter la comparaison', df, 'retailflow_comparaison_caisses.csv', 'rf_scenario_export')


def render_sensitivity(config: ScenarioConfig, strategy: str) -> None:
    """Répétitions avec graines différentes et incertitude descriptive."""
    _heading('Robustesse des résultats', 'Tester plusieurs graines aléatoires au lieu de conclure sur un seul tirage.')
    runs = st.slider('Nombre de répétitions', 3, 20, 5, key='rf_repetitions')
    start_seed = st.number_input('Première graine', 0, 100000, int(config.seed or 42), key='rf_repetitions_seed')
    if st.button('Calculer les répétitions', type='primary', key='rf_run_repetitions'):
        with st.spinner('Simulation des répétitions en cours…'):
            df = _repeat_runs(config, strategy, int(runs), int(start_seed))
        st.session_state['rf_repetition_data'] = df
        st.session_state['rf_repetition_signature'] = (config, strategy, runs, int(start_seed))
    df = st.session_state.get('rf_repetition_data')
    signature = st.session_state.get('rf_repetition_signature')
    if df is None or signature != (config, strategy, runs, int(start_seed)):
        st.info('Clique sur « Calculer les répétitions » pour lancer cette analyse optionnelle.')
        return
    a, b, c = st.columns(3)
    a.metric('Attente moyenne des répétitions', _minutes(df['attente_moy_min'].mean()))
    b.metric('Écart-type entre répétitions', _minutes(df['attente_moy_min'].std(ddof=1)))
    c.metric('Pire moyenne observée', _minutes(df['attente_moy_min'].max()))
    st.plotly_chart(_chart_line(df.rename(columns={'graine': 'minute'}), 'minute',
                               ['attente_moy_min', 'attente_p90_min'],
                               'Variation selon la graine aléatoire'), use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    _csv_button('Exporter les répétitions', df, 'retailflow_repetitions.csv', 'rf_repetitions_export')
    st.caption('L’écart-type est descriptif. Aucune marge d’erreur ni significativité n’est affirmée.')


@st.cache_data(show_spinner='Simulations répétées…')
def _repeat_runs(config: ScenarioConfig, strategy: str, count: int, first_seed: int) -> pd.DataFrame:
    rows = []
    for seed in range(first_seed, first_seed + count):
        result = SimulationEngine(build_strategy(strategy)).run(config.with_seed(seed))
        kpi = KpiCalculator().compute(result)
        rows.append({
            'graine': seed,
            'attente_moy_min': kpi.mean_wait,
            'attente_p90_min': kpi.p90_wait,
            'part_longue_pct': 100 * kpi.share_over_threshold,
            'occupation_pct': 100 * kpi.mean_utilization,
        })
    return pd.DataFrame(rows)


def _csv_button(label: str, df: pd.DataFrame, filename: str, key: str) -> None:
    st.download_button(
        label, data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name=filename, mime='text/csv', key=key,
    )


def _json_bytes(config: ScenarioConfig, strategy: str, s: StudioSummary) -> bytes:
    payload = {
        'application': 'RetailFlow',
        'schema_version': 1,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'config': asdict(config),
        'strategy': strategy,
        'summary': asdict(s),
        'notes': ['Simulation synthétique', 'Temps en minutes', 'Le moteur historique ne simule pas les abandons'],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')


def _markdown_report(config: ScenarioConfig, strategy: str, s: StudioSummary, registers: pd.DataFrame) -> str:
    lines = [
        '# RetailFlow : rapport de simulation',
        '',
        '## Contexte',
        '',
        f'- Scénario : {config.name}',
        f'- Stratégie : {strategy}',
        f'- Graine : {config.seed}',
        f'- Clients : {s.customers}',
        f'- Caisses : {s.registers}',
        f'- Fenêtre des arrivées : {config.arrival_window_min:.1f} min',
        f'- Durée moyenne paramétrée du service : {config.mean_service_time_min:.1f} min',
        '',
        '## Indicateurs',
        '',
        '| Indicateur | Valeur |',
        '|---|---:|',
        f'| Attente moyenne | {s.mean_wait:.2f} min |',
        f'| Attente médiane | {s.median_wait:.2f} min |',
        f'| Attente P90 | {s.p90_wait:.2f} min |',
        f'| Attente maximale | {s.maximum_wait:.2f} min |',
        f'| Niveau de service ≤ 5 min | {s.service_level * 100:.2f} % |',
        f'| Durée totale | {s.duration:.2f} min |',
        f'| Débit moyen | {s.throughput:.2f} clients/h |',
        '',
        '## Caisses',
        '',
        '| Caisse | Clients | Attente moyenne (min) | Occupation (%) |',
        '|---|---:|---:|---:|',
    ]
    for row in registers.itertuples(index=False):
        lines.append(f'| {row.caisse} | {row.clients} | {row.attente_moy_min:.2f} | {row.occupation_pct:.2f} |')
    lines.extend([
        '',
        '## Méthode et limites',
        '',
        '- Données générées par simulation, non observées dans un magasin réel.',
        '- Moteur historique : files FIFO, sans abandon ni changement de caisse en cours de route.',
        '- Résultats conditionnés aux paramètres et à la graine aléatoire.',
        '- Le seuil de 5 minutes est une hypothèse analytique.',
        '- Les comparaisons doivent être répétées sur plusieurs graines avant décision.',
        '',
    ])
    return '\n'.join(lines)


def render_exports(config: ScenarioConfig, strategy: str, result: SimulationResult) -> None:
    """Exports CSV, JSON et rapport Markdown reproductible."""
    _heading('Centre d’export', 'Données et rapports de simulation.')
    customers = customer_frame(result)
    registers = register_frame(result)
    timeline = timeline_frame(result, max(1., result.end_time / 200))
    s = summary(result)
    a, b = st.columns(2)
    with a:
        st.markdown('#### Données détaillées')
        _csv_button('CSV : clients', customers, 'retailflow_clients.csv', 'rf_export_customers')
        _csv_button('CSV : caisses', registers, 'retailflow_caisses.csv', 'rf_export_registers')
        _csv_button('CSV : chronologie', timeline, 'retailflow_chronologie.csv', 'rf_export_timeline')
        _csv_button('CSV : événements', event_frame(result), 'retailflow_evenements.csv', 'rf_export_events')
    with b:
        st.markdown('#### Rapports')
        st.download_button('JSON : paramètres et KPI', _json_bytes(config, strategy, s),
                           file_name='retailflow_resume.json', mime='application/json', key='rf_export_json')
        report = _markdown_report(config, strategy, s, registers)
        st.download_button('Markdown : rapport de simulation', report.encode('utf-8'),
                           file_name='retailflow_rapport.md', mime='text/markdown', key='rf_export_md')
        with st.expander('Prévisualiser le rapport Markdown'):
            st.markdown(report)
    st.caption('Les exports contiennent uniquement les données de simulation, sans données personnelles réelles.')


def render_methodology(config: ScenarioConfig, result: SimulationResult) -> None:
    """Transparence sur hypothèses et limites, utile à la soutenance."""
    _heading('Méthodologie et limites', 'Comprendre ce que les indicateurs mesurent réellement.')
    with st.expander('1. Génération des clients', expanded=True):
        st.write('Le générateur crée des instants d’arrivée et des durées de service synthétiques. '
                 'Une graine fixée permet de reproduire les mêmes tirages.')
        st.code(f'clients = {config.customer_count}\nfenetre = {config.arrival_window_min} min\nseed = {config.seed}', language='text')
    with st.expander('2. Affectation aux caisses'):
        st.write('La stratégie sélectionnée détermine la caisse à laquelle le client est affecté. '
                 'Chaque caisse traite ses clients dans l’ordre prévu par le moteur historique.')
    with st.expander('3. Définition du temps d’attente'):
        st.latex(r'W_i = t_{debut\,service,i} - t_{arrivee,i}')
        st.write('Le temps de service est distinct du temps d’attente.')
    with st.expander('4. Indicateurs de performance'):
        st.latex(r'\overline{W} = \frac{1}{N}\sum_{i=1}^{N} W_i')
        st.write('Le P90 est le 90e percentile interpolé des temps d’attente.')
        st.write('L’occupation d’une caisse correspond au temps cumulé de service divisé par la durée de simulation.')
    with st.expander('5. Hypothèses de la version historique'):
        st.write('Les caisses ne s’ouvrent ni ne ferment dynamiquement. Les clients ne changent pas de file et n’abandonnent pas. '
                 'Le moteur dynamique, disponible séparément, traite ces mécanismes.')
    with st.expander('6. Interprétation des résultats'):
        st.write('Il ne faut pas confondre corrélation et causalité. Une caisse plus lente peut avoir reçu des clients '
                 'avec des durées de service différentes. Une seule graine ne suffit pas à établir la robustesse.')
    with st.expander('7. Reproductibilité'):
        st.write('Conserver les paramètres, la stratégie, la graine, les versions des dépendances et les exports.')
        st.json({'scenario': config.name, 'seed': config.seed, 'clients': len(result.customers), 'registers': config.open_registers})


def render_studio(config: ScenarioConfig, strategy: str, result: SimulationResult) -> None:
    """Point d’entrée unique pour les analyses avancées.

    Les onglets historiques sont conservés pour compatibilité avec les tests.
    Les calculs lourds sont mis en cache et lancés sur demande.
    """
    st.markdown('---')
    st.markdown('## RetailFlow Studio')
    st.caption('Centre de contrôle analytique : exploration, comparaison, reproductibilité et exports.')
    names = [
        'Vue exécutive', 'Attentes', 'Caisses', 'Flux', 'Clients',
        'Arrivées', 'Scénarios', 'Robustesse', 'Diagnostic', 'Glossaire', 'Exports', 'Méthodologie',
    ]
    choice = st.segmented_control('Espace de travail', names, default=names[0], key='rf_studio_nav')
    if choice == 'Vue exécutive':
        render_overview(result)
    elif choice == 'Attentes':
        render_waits(result)
    elif choice == 'Caisses':
        render_registers(result)
    elif choice == 'Flux':
        render_flow(result)
    elif choice == 'Clients':
        render_customer_explorer(result)
    elif choice == 'Arrivées':
        render_arrivals(result)
    elif choice == 'Scénarios':
        render_scenarios(config, strategy)
    elif choice == 'Robustesse':
        render_sensitivity(config, strategy)
    elif choice == 'Diagnostic':
        render_diagnostics(result)
    elif choice == 'Glossaire':
        render_glossary()
    elif choice == 'Exports':
        render_exports(config, strategy, result)
    elif choice == 'Méthodologie':
        render_methodology(config, result)
    st.markdown('---')
    st.caption('RetailFlow | Simulation pédagogique | Données synthétiques | Résultats dépendants des hypothèses')


def diagnostic_rules(result: SimulationResult) -> list[dict[str, str]]:
    """Règles explicables, sans prétendre à une optimisation causale."""
    s = summary(result)
    reg = register_frame(result)
    findings = []
    if s.mean_wait > WAIT_TARGET:
        findings.append({
            'priorite': 'Élevée',
            'constat': 'Attente moyenne élevée',
            'preuve': f'{s.mean_wait:.2f} min > {WAIT_TARGET:.1f} min',
            'action': 'Comparer plusieurs capacités et plusieurs graines.',
        })
    if s.p90_wait > WAIT_TARGET:
        findings.append({
            'priorite': 'Élevée',
            'constat': 'Queue de distribution défavorable',
            'preuve': f'P90 = {s.p90_wait:.2f} min',
            'action': 'Analyser les arrivées pendant les pics et le risque de congestion.',
        })
    if s.service_level < .9:
        findings.append({
            'priorite': 'Moyenne',
            'constat': 'Niveau de service sous 90 %',
            'preuve': f'{100 * s.service_level:.1f} % des clients attendent 5 min ou moins',
            'action': 'Étudier les files les plus longues et tester un scénario alternatif.',
        })
    if len(reg) > 1:
        max_occ = float(reg['occupation_pct'].max())
        min_occ = float(reg['occupation_pct'].min())
        if max_occ - min_occ > 25:
            findings.append({
                'priorite': 'Moyenne',
                'constat': 'Occupation hétérogène',
                'preuve': f'Écart de {max_occ - min_occ:.1f} points entre caisses',
                'action': 'Examiner la répartition des clients et la variabilité des services.',
            })
    if s.maximum_wait > 2 * WAIT_TARGET:
        findings.append({
            'priorite': 'Moyenne',
            'constat': 'Attente extrême observée',
            'preuve': f'Maximum = {s.maximum_wait:.2f} min',
            'action': 'Examiner le parcours du client concerné et la minute de son arrivée.',
        })
    if not findings:
        findings.append({
            'priorite': 'Information',
            'constat': 'Aucune alerte déclenchée',
            'preuve': 'Les seuils heuristiques de cette page ne sont pas dépassés',
            'action': 'Contrôler tout de même la robustesse avec plusieurs graines.',
        })
    return findings


def render_diagnostics(result: SimulationResult) -> None:
    """Lecture guidée des KPI avec transparence des règles."""
    _heading('Diagnostic assisté', 'Alertes déterministes construites sur des seuils explicites.')
    findings = diagnostic_rules(result)
    st.dataframe(pd.DataFrame(findings), use_container_width=True, hide_index=True)
    for finding in findings:
        tone = 'red' if finding['priorite'] == 'Élevée' else 'gold'
        _callout(finding['constat'], finding['preuve'] + '. ' + finding['action'], tone)
    st.caption('Ces alertes suivent des règles explicites et des seuils paramétrables.')
    _csv_button('Exporter les alertes', pd.DataFrame(findings), 'retailflow_diagnostic.csv', 'rf_diagnostics_export')


def render_glossary() -> None:
    """Mini-glossaire pour la soutenance et l’interprétation des graphiques."""
    _heading('Glossaire technique', 'Définitions des notions utilisées dans RetailFlow.')
    glossary = [
        ('FIFO', 'First In, First Out : premier arrivé, premier servi.'),
        ('Simulation à événements discrets', 'Modèle dont les changements d’état surviennent à des instants déterminés.'),
        ('Graine aléatoire', 'Valeur initialisant le générateur pseudo-aléatoire pour reproduire un tirage.'),
        ('Temps d’attente', 'Durée entre l’arrivée du client et le début de son service.'),
        ('Temps de service', 'Durée pendant laquelle la caisse traite le client.'),
        ('Temps dans le système', 'Somme du temps d’attente et du temps de service.'),
        ('Débit', 'Nombre de clients servis par unité de temps.'),
        ('Taux d’occupation', 'Part de la durée totale consacrée au service par une caisse.'),
        ('P90', 'Valeur sous laquelle se trouvent 90 % des observations.'),
        ('Médiane', 'Valeur partageant les observations ordonnées en deux groupes.'),
        ('Variance', 'Mesure de dispersion des observations autour de leur moyenne.'),
        ('Analyse de sensibilité', 'Étude de la variation des résultats quand un paramètre change.'),
        ('Réplication', 'Nouvelle exécution de la simulation avec une autre graine.'),
        ('Congestion', 'Situation dans laquelle les arrivées dépassent temporairement la capacité de traitement.'),
        ('Niveau de service', 'Part des clients respectant un seuil d’attente défini.'),
        ('Biais de simulation', 'Écart possible entre les hypothèses du modèle et le fonctionnement réel.'),
        ('Validation', 'Vérification que le modèle représente suffisamment bien l’usage visé.'),
        ('Vérification', 'Contrôle que le code applique correctement les règles définies.'),
        ('Heuristique', 'Règle pratique utile mais sans garantie d’optimalité globale.'),
        ('Reproductibilité', 'Possibilité de retrouver les mêmes résultats avec les mêmes entrées.'),
    ]
    query = st.text_input('Rechercher une notion', key='rf_glossary_query').strip().lower()
    selected = [(term, definition) for term, definition in glossary if query in (term + ' ' + definition).lower()]
    for term, definition in selected:
        with st.expander(term):
            st.write(definition)
    st.caption(f'{len(selected)} notion(s) affichée(s) sur {len(glossary)}.')
