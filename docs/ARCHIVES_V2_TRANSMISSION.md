# RetailFlow | Archives V2 : transmission et intégration

> **Document historique.** Ce texte décrit l'état du projet au moment de cette étape. Les branches, commandes, chiffres de tests et tâches « à faire » peuvent être obsolètes. Pour la version actuelle, consulter [l'index documentaire](README.md) et [la validation V7](VERSION_7_VALIDATION.md).

## 1. Modules disponibles

- `queuesmart/simulation/dynamic.py` : moteur dynamique indépendant du moteur historique.
- `dynamic_demo.py` : banc d'essai Streamlit, lancé séparément de `app.py`.
- `queuesmart/simulation/events.py` : événements historiques, pour la simulation FIFO statique uniquement.
- `queuesmart/analytics/mean_wait_optimizer.py` : optimisation sur l'attente moyenne, pour le moteur historique.
- `tests/test_dynamic.py` : tests du nouveau moteur.

## 2. Visualisation 2D : contrat des événements

Lancer `DynamicSimulationEngine().run(config, options)` et lire `result.events`.
Chaque événement contient : `time` (minutes simulées), `type`, `customer_id`, `register_id`, `target_register_id`, `queue_position`.
Événements : `customer_arrived`, `queue_joined`, `service_started`, `customer_departed`, `queue_switched`, `customer_abandoned`, `register_opened`, `register_closed`.
Le moteur produit tous les événements en une fois, puis la 2D les rejoue à vitesse x1 à x5. Ne pas créer un deuxième moteur dans JavaScript. Ne pas supposer qu'un `queue_position` est présent pour chaque événement : il faut recalculer la position à partir des files lors des départs et changements.
Une fermeture termine le service en cours et réaffecte les clients en attente. La dernière caisse ouverte ne ferme pas.

## 3. Analytics : populations et indicateurs

`result.customers` contient les arrivées, les débuts de service, les départs, les abandons et les durées de service. `result.mean_wait_served` exclut les clients abandonnés. `result.served_count` et `result.abandoned_count` sont disjoints.
**Attention :** l'ancien `KpiCalculator` est conçu pour `SimulationResult` et ne doit pas être appliqué directement à `DynamicResult`. Développer un adaptateur dédié et documenter la population de chaque indicateur.
`mean_wait_optimizer.py` optimise pour l'instant le moteur historique, pas le moteur dynamique. Pour l'optimiseur dynamique, comparer 1 à 5 caisses avec les mêmes arrivées, la même graine et les mêmes hypothèses.

## 4. Intégration dans Streamlit

L'application historique `app.py` n'a pas été remplacée. Lancer `dynamic_demo.py` pour valider le moteur. Le contrôle « ouvrir/fermer » est actuellement programmé à une minute simulée avant l'exécution, pas encore un contrôle interactif pendant l'animation. La synchronisation live et la scène pixel art sont à réaliser.

## 5. Installation et vérification

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run dynamic_demo.py
```

## 6. Limites connues

- Choix de caisse basé sur la durée exacte restante, hypothèse optimiste à expliciter.
- Patience identique pour tous les clients, configurable, sans profils multiples.
- Le moteur ne simule pas les trajets spatiaux : la 2D gère uniquement les interpolations visuelles.
- Les changements de caisse sont définis par un calendrier de simulation, pas par un appel réseau en temps réel.
- Les statistiques du dashboard historique ne reflètent pas encore le nouveau moteur.
- Le plafond 1 à 5 caisses est appliqué au moteur dynamique, pas à l'interface historique.


## 7. Collaboration GitHub

- Branche 2D : `feature/simulation-2d`.
- Branche analytics : `feature/dashboard-analytics`.
- Branche commune : `main`, fusion uniquement après revue et tests.
- Cette V2 est prioritaire sur le contrat historique V1 pour les événements du moteur dynamique.
