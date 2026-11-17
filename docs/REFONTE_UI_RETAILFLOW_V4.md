# RetailFlow V4 : refonte Streamlit et centre analytique

## Objectif

Améliorer l'expérience visuelle et les fonctionnalités sans réécrire le moteur métier existant. Le module `queuesmart/ui/insights.py` ajoute plus de 800 lignes de code fonctionnel, avec 12 espaces d'analyse accessibles sous les trois onglets historiques.

## Espaces ajoutés

1. Vue exécutive : indicateurs, courbes d'activité, jauge d'attente.
2. Attentes : histogrammes, classes, percentiles et équité entre arrivants.
3. Caisses : occupation, charge, attente moyenne et P90.
4. Flux : files, sorties, chronologie des événements.
5. Clients : filtres, parcours individuel et export.
6. Arrivées : pics d'affluence et répartition des services.
7. Scénarios : comparaison de 1 à 8 caisses, à graine constante.
8. Robustesse : répétitions avec différentes graines.
9. Diagnostic : règles explicables et alertes.
10. Glossaire : notions de simulation et de statistique.
11. Exports : CSV, JSON et rapport Markdown.
12. Méthodologie : hypothèses, formules, limites et reproductibilité.

## Points de vigilance

- La scène 2D définitive et les modules des autres membres ne sont pas intégrés.
- Les analyses du Studio portent sur le moteur historique, pas sur le moteur dynamique.
- Les changements de file, abandons et ouvertures/fermetures dynamiques sont dans `dynamic_demo.py`.
- Les simulations comparatives ne doivent pas être interprétées comme des résultats sur des clients réels.
- Le moteur historique permet jusqu'à 8 caisses. Le périmètre final de 5 caisses reste à harmoniser.

## Démarrage

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

## Publication GitHub

Créer le dépôt `RetailFlow`, vérifier `.gitignore`, puis publier seulement après validation locale du rendu et des tests Streamlit.
