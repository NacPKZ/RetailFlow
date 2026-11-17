# SuperQueue - Contrat d'intégration V1

## Statut

Le moteur historique calcule des files FIFO fixes. Les modules `queuesmart.simulation.events` et `queuesmart.analytics.mean_wait_optimizer` ont été ajoutés sans modifier les calculs existants.

## Pour le membre 2 : visualisation 2D

Importer `events_from_result(result)` après `SimulationEngine.run(config)`.

Chaque événement possède : `time` (minutes simulées), `type`, `customer_id`, `register_id`, `queue_position` (uniquement pour `queue_joined`). Utiliser `event.to_dict()` pour obtenir un dictionnaire sérialisable en JSON.

Types actuellement disponibles : `customer_arrived`, `queue_joined`, `service_started`, `customer_departed`.

Pour le mouvement, l'animation doit interpoler les positions entre événements. Le moteur décide des caisses et des instants, pas le dessin. Ne pas simuler aléatoirement des événements côté navigateur.

Attention : les événements de file peuvent partager le même instant. Ils sont triés de manière déterministe. La représentation graphique des rangs devra être vérifiée dans les scénarios simultanés.

Non disponible en V1 : `queue_switched`, `customer_abandoned`, `register_opened`, `register_closed`. Ne pas prétendre que ces comportements sont déjà simulés.

## Pour le membre 3 : dashboard

Utiliser `KpiCalculator().compute(result)` pour les KPI historiques et `recommend_by_mean_wait(engine, calculator, config, threshold_min, max_registers=5)` pour l'objectif du nouveau cahier des charges.

`MeanWaitRecommendation` contient `recommended_registers` (ou `None`), `mean_wait_by_register_count` et `threshold_min`.

Les simulations comparées utilisent la même graine, mais les temps de service et arrivées sont seulement comparables dans les limites du générateur historique. L'optimisation V1 utilise une seule réplication : signaler cette limite. Ne pas afficher de taux d'abandon ou de changements de file calculés tant que le moteur ne les gère pas.

## Pour le responsable intégration

Ne pas remplacer les modules historiques. Exécuter les tests de non-régression avant toute fusion. Conserver Streamlit pour le conteneur principal. La visualisation 2D peut être un composant JavaScript embarqué, mais elle ne doit jamais recalculer les événements métier.

## Démonstration minimale

```python
from queuesmart.config import ScenarioConfig
from queuesmart.simulation.engine import SimulationEngine
from queuesmart.simulation.strategies import build_strategy
from queuesmart.simulation.events import events_from_result
from queuesmart.analytics.kpi import KpiCalculator
from queuesmart.analytics.mean_wait_optimizer import recommend_by_mean_wait

engine = SimulationEngine(build_strategy("shortest_queue"))
config = ScenarioConfig("Démo", 30, 30.0, 2.0, 3, seed=42)
result = engine.run(config)
events = [e.to_dict() for e in events_from_result(result)]
recommendation = recommend_by_mean_wait(engine, KpiCalculator(), config, 5.0)
print(len(events), recommendation.recommended_registers)
```

## Reste à faire avant livraison complète

1. Concevoir un moteur dynamique avec une véritable horloge d'événements, gestion des files, patience et changements de file.
2. Définir et tester l'ouverture et fermeture des caisses pendant l'exécution.
3. Vérifier les KPI et leur définition en présence d'abandons.
4. Tester l'intégration Streamlit et le rendu 2D en navigateur.
5. Ajouter les tests d'interface et de bout en bout.
