"""Banc d'essai Streamlit du moteur dynamique, indépendant de l'app historique.

Lancer : python -m streamlit run dynamic_demo.py
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from queuesmart.ui.theme import apply_theme, hero
import streamlit as st

from queuesmart.config import ScenarioConfig
from queuesmart.simulation.dynamic import DynamicOptions, DynamicSimulationEngine
from queuesmart.ui.scene_view import render_scene_2d

st.set_page_config(page_title='RetailFlow | Validation dynamique', layout='wide')
apply_theme()
hero('Simulation dynamique', 'Moteur événementiel : arrivées, changements de file, abandons et caisses.', 'RETAILFLOW | VALIDATION TECHNIQUE')
st.caption('Banc d’essai technique, distinct de la future scène pixel art.')
with st.sidebar:
    count = st.slider('Clients', 1, 100, 60)
    registers = st.slider('Caisses initialement ouvertes', 1, 5, 3)
    arrivals = st.slider('Fenêtre des arrivées (min)', 5, 120, 45)
    service = st.slider('Durée moyenne de service (min)', 0.3, 8.0, 2.0)
    seed = st.number_input('Graine aléatoire', 0, 100000, 42)
    patience = st.slider('Patience avant abandon (min)', 1, 60, 12)
    switches = st.checkbox('Changements de file', value=True)
    st.subheader('Changement programmé de caisse')
    change = st.selectbox('Action', ['Aucune', 'Ouvrir', 'Fermer'])
    change_register = st.selectbox('Caisse concernée', [1, 2, 3, 4, 5])
    change_time = st.number_input('Minute du changement', min_value=0.0, value=10.0)

changes = () if change == 'Aucune' else ((float(change_time), change_register, change == 'Ouvrir'),)
config = ScenarioConfig('Démo dynamique', count, arrivals, service, registers, seed=int(seed))
options = DynamicOptions(patience_min=patience, switching_enabled=switches, register_changes=changes)
result = DynamicSimulationEngine().run(config, options)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Clients', len(result.customers))
c2.metric('Servis', result.served_count)
c3.metric('Abandons', result.abandoned_count)
c4.metric('Attente moyenne des servis', f'{result.mean_wait_served:.2f} min' if result.mean_wait_served is not None else 'N/A')
st.caption(f'Graine : {int(seed)} | Caisses initiales : {registers} | Durée des arrivées : {arrivals} min')
st.subheader('Scène 2D')
render_scene_2d(result)
st.subheader('Vue analytique')
left, right = st.columns(2)
with left:
    event_counts = pd.DataFrame(result.events_as_dicts())
    if not event_counts.empty:
        counts = event_counts.groupby('type').size().rename('Nombre').reset_index()
        fig = px.bar(counts, x='type', y='Nombre', title='Événements par type', color_discrete_sequence=['#2862a4'])
        fig.update_layout(xaxis_title='', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#14233b')
        st.plotly_chart(fig, use_container_width=True)
with right:
    waits = [c.wait_time for c in result.customers if c.service_start is not None]
    if waits:
        fig = px.histogram(x=waits, nbins=20, title='Distribution des attentes des clients servis', labels={'x':'Attente (min)', 'y':'Clients'}, color_discrete_sequence=['#d6a858'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#14233b')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('Aucun client servi pour cette configuration.')

events = pd.DataFrame(result.events_as_dicts())
st.subheader('Événements horodatés')
st.dataframe(events, use_container_width=True, hide_index=True)
st.download_button('Exporter les événements (CSV)', events.to_csv(index=False).encode('utf-8-sig'), 'evenements_retailflow.csv', 'text/csv')

customers = pd.DataFrame([{
    'customer_id': c.customer_id, 'arrival_time': c.arrival_time,
    'register_id': c.register_id, 'service_start': c.service_start,
    'departure_time': c.departure_time, 'abandoned_at': c.abandoned_at,
    'wait_time': c.wait_time,
} for c in result.customers])
st.subheader('Résultats par client')
st.dataframe(customers, use_container_width=True, hide_index=True)
st.download_button('Exporter les clients (CSV)', customers.to_csv(index=False).encode('utf-8-sig'), 'clients_retailflow.csv', 'text/csv')


st.info('Une caisse fermée termine son client en service et réaffecte les clients encore en attente. La dernière caisse ouverte ne peut pas être fermée.')
