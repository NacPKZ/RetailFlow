# RetailFlow | Architecture et choix de conception

## Architecture de l’application V8

`app.py` est l’entrée Streamlit. Les cinq espaces partagent configuration latérale, thème et historique de navigation. La scène utilise `ui/dynamic_view.py` pour ses réglages et actions. `ui/dynamic_dashboard.py` analyse le même résultat, et les deux objectifs d’optimisation utilisent les tirages de `analytics/decision_lab.py`. Les analyses et comparaisons FIFO restent accessibles avec leur propre périmètre.

Le journal dynamique alimente les trajectoires et les séries KPI en Python. Le Canvas lit les trajectoires et émet les commandes. Les exports reprennent les tables affichées. Voir [les contrats analytiques](DICTIONNAIRE_KPI_DYNAMIQUES.md) et [les arbitrages](INTEGRATION_MISSION_3.md).

Les sections suivantes documentent aussi les choix et contrats historiques du moteur FIFO.


## Architecture en couches

Les dépendances vont **dans un seul sens**. Une couche n'importe jamais une couche située au-dessus d'elle.

```mermaid
flowchart LR
    ui["ui/<br/>(Streamlit, Plotly)"] --> analytics["analytics/<br/>(KPI, recommandation)"]
    analytics --> simulation["simulation/<br/>(générateur, stratégies, moteur, résultat)"]
    ui --> simulation
    simulation --> domain["domain/<br/>(Customer, CheckoutRegister)"]
    domain --> base["config.py · exceptions.py"]
```

- **Seul `ui/` importe Streamlit.** Le moteur et les KPI se testent donc sans interface.
- Dans `ui/`, la logique calculable est séparée du rendu :
  `store_layout.py` et `client_board.py` sont **purs et testés**, tandis que `store_view.py`,
  `client_screen.py`, `sidebar.py` et `dashboard.py` ne font qu'afficher.
- `app.py` ne fait qu'assembler : il lit la barre latérale, lance la simulation (mise en cache)
  et appelle les 3 fonctions de rendu.

## Diagramme de classes (UML)

```mermaid
classDiagram
    direction LR

    class ScenarioConfig {
        <<frozen dataclass>>
        +name: str
        +customer_count: int
        +arrival_window_min: float
        +mean_service_time_min: float
        +open_registers: int
        +seed: int | None
        +arrival_rate_per_min() float
        +with_registers(n) ScenarioConfig
        +with_seed(seed) ScenarioConfig
    }

    class Customer {
        <<dataclass>>
        +customer_id: int
        +arrival_time: float
        +service_duration: float
        +register_id: int | None
        +service_start: float | None
        +assign(register_id, service_start)
        +is_served() bool
        +service_end() float
        +wait_time() float
        +is_waiting_at(t) bool
        +is_being_served_at(t) bool
        +is_present_at(t) bool
    }

    class CheckoutRegister {
        -_register_id: int
        -_customers: list~Customer~
        +register_id() int
        +customers() tuple~Customer~
        +busy_until() float
        +serve(customer)
        +queue_length_at(t) int
        +estimated_wait_at(t) float
        +busy_time() float
    }

    class AssignmentStrategy {
        <<abstract>>
        +name: str
        +label: str
        +choose(registers, t)* CheckoutRegister
    }
    class ShortestQueueStrategy
    class LeastWaitStrategy

    class CustomerGenerator {
        -_config: ScenarioConfig
        +generate() list~Customer~
    }

    class SimulationEngine {
        -_strategy: AssignmentStrategy
        +strategy() AssignmentStrategy
        +run(config) SimulationResult
    }

    class SimulationResult {
        <<frozen dataclass>>
        +config: ScenarioConfig
        +strategy_name: str
        +customers: tuple~Customer~
        +registers: tuple~CheckoutRegister~
        +end_time() float
        +customer(id) Customer
        +snapshot_at(t) StoreSnapshot
        +timeline(step) list~StoreSnapshot~
    }

    class StoreSnapshot {
        <<frozen dataclass>>
        +time: float
        +registers: tuple~RegisterSnapshot~
        +not_arrived_count: int
        +departed_count: int
    }

    class RegisterSnapshot {
        <<frozen dataclass>>
        +register_id: int
        +serving_customer_id: int | None
        +waiting_customer_ids: tuple~int~
        +estimated_wait: float
        +queue_length() int
    }

    class KpiCalculator {
        -_wait_threshold_min: float
        +compute(result) KpiReport
        +compute_many(results) KpiReport
    }
    class KpiReport {
        <<frozen dataclass>>
        +mean_wait, median_wait, p90_wait, max_wait
        +share_over_threshold: float
        +mean_utilization: float
        +utilization_by_register: dict
    }
    class ServiceTarget {
        <<frozen dataclass>>
        +max_p90_wait_min: float
        +max_share_over_threshold: float
        +is_met_by(report) bool
    }
    class RegisterRecommender {
        +recommend(base) Recommendation
    }
    class Recommendation {
        <<frozen dataclass>>
        +recommended_registers: int | None
        +reports_by_register_count: dict
        +target: ServiceTarget
    }

    class StoreLayout {
        +register_position(id) tuple
        +place_customers(snapshot, result) list~PlacedCustomer~
    }
    class PlacedCustomer {
        <<frozen dataclass>>
        +customer_id, x, y, state, wait_so_far
    }
    class BoardLine {
        <<frozen dataclass>>
        +register_id, estimated_wait, queue_length, is_recommended
    }

    AssignmentStrategy <|-- ShortestQueueStrategy
    AssignmentStrategy <|-- LeastWaitStrategy
    CheckoutRegister o-- "0..*" Customer : sert (FIFO)
    SimulationEngine *-- AssignmentStrategy : délègue le choix
    SimulationEngine ..> CustomerGenerator : utilise
    CustomerGenerator ..> ScenarioConfig : lit
    CustomerGenerator ..> Customer : crée
    SimulationEngine ..> SimulationResult : produit
    SimulationResult *-- ScenarioConfig
    SimulationResult *-- "1..*" Customer
    SimulationResult *-- "1..8" CheckoutRegister
    SimulationResult ..> StoreSnapshot : produit
    StoreSnapshot *-- "1..8" RegisterSnapshot
    KpiCalculator ..> SimulationResult : lit
    KpiCalculator ..> KpiReport : produit
    RegisterRecommender *-- SimulationEngine
    RegisterRecommender *-- KpiCalculator
    RegisterRecommender *-- ServiceTarget
    RegisterRecommender ..> Recommendation : produit
    Recommendation *-- KpiReport
    StoreLayout ..> StoreSnapshot : lit
    StoreLayout ..> PlacedCustomer : produit
```

Fonctions (hors classes) : `build_strategy` et le registre `STRATEGIES` (stratégies),
`compare_strategies`, `compare_scenarios`, `run_replications` et `relative_gain`
(`analytics/comparison.py`), `build_board` et `format_minutes` (`ui/client_board.py`),
`wait_level`, `describe_status` et `animation_step` (`ui/store_layout.py`).

## Responsabilités

| Classe / module | Responsabilité unique |
|---|---|
| `ScenarioConfig` | décrire un scénario **valide** (validation à la création, immuable) |
| `Customer` | connaître son propre parcours : arrivée, début, fin, attente, état à l'instant t |
| `CheckoutRegister` | servir ses clients en FIFO sans chevauchement, et répondre « combien de clients ? combien d'attente ? » |
| `CustomerGenerator` | produire des clients aléatoires mais reproductibles |
| `AssignmentStrategy` et ses sous-classes | choisir une caisse |
| `SimulationEngine` | orchestrer : générer, faire choisir, faire servir |
| `SimulationResult` | exposer le résultat et reconstituer l'état du magasin à tout instant |
| `KpiCalculator` | transformer des résultats en indicateurs |
| `RegisterRecommender` | trouver le plus petit nombre de caisses qui atteint la `ServiceTarget` |
| `StoreLayout` | calculer la géométrie de la vue 2D |
| `build_board` | calculer le contenu du panneau client |

## Choix de conception (et pourquoi)

1. **Composition et polymorphisme pour les comportements.** Le moteur *a* une stratégie et lui
   délègue le choix. Ajouter un comportement ne touche ni au moteur ni à l'interface : il suffit
   d'une sous-classe et d'une entrée dans `STRATEGIES` (principe ouvert/fermé). C'est le seul
   héritage du projet, et c'est là qu'il apporte de la valeur.
2. **Objets immuables aux frontières.** `ScenarioConfig`, `SimulationResult`, les snapshots et
   les rapports sont des `frozen dataclass`. L'interface ne peut donc pas modifier un résultat
   par erreur, et le cache Streamlit est sûr.
3. **Encapsulation de la caisse.** La liste `_customers` est privée, n'est exposée qu'en
   `tuple` et n'est alimentée que par `serve()`. L'invariant « pas de chevauchement » ne
   peut donc pas être violé de l'extérieur.
4. **Une seule définition de chaque notion (DRY).** L'attente est `Customer.wait_time`, la
   « longueur de file » est le nombre de clients présents (domaine et snapshot), et toutes
   les durées passent par `format_minutes`.
5. **Validation précoce et erreurs typées.** Une configuration invalide ne peut pas exister.
   Les erreurs métier héritent de `QueueSmartError`, avec des messages en français affichés
   tels quels par l'interface (`st.error`, `st.warning`), jamais de traceback.
6. **Recommandation robuste.** Une seule simulation dépend trop du hasard. Pour chaque nombre
   de caisses de 1 à 8, on lance 20 simulations (graines `seed`, `seed+1`, …) et on regroupe
   les attentes de tous les clients avant de calculer le p90. On retient le **plus petit**
   nombre de caisses qui respecte la cible, car chaque caisse coûte du personnel.
7. **Constantes centralisées.** Les valeurs métier sont dans `config.py`. Les constantes
   d'affichage (couleurs, tailles, pas d'animation) sont nommées en tête de leur module `ui/`.
8. **Simplicité.** Dans le moteur historique, il n'y a pas de simulation à événements discrets : en FIFO sans abandon,
   le début de service se calcule à l'arrivée, et une boucle suffit.

## Extensions au contrat d'interface initial

Elles ajoutent des éléments sans rien modifier de l'existant :

- `Customer.is_present_at(t)` : « en attente ou en service ». Elle évite de répéter cette
  condition dans `CheckoutRegister` et dans les snapshots ;
- constantes `MAX_SHARE_OVER_THRESHOLD` et bornes de saisie (`MAX_CUSTOMER_COUNT`, …) dans `config.py` ;
- module `analytics/comparison.py` : répétition de simulations et comparaisons, partagées par
  le recommandeur et le dashboard (DRY) ;
- `wait_level`, `describe_status` et `animation_step` dans `ui/store_layout.py` : logique pure de l'animation.


## Évolution de l'architecture

RetailFlow conserve le package Python historique `queuesmart` afin de préserver les imports et les tests. Deux moteurs coexistent : `SimulationEngine` (FIFO historique, utilisé dans `app.py`) et `DynamicSimulationEngine` (événements discrets, validé dans `dynamic_demo.py`). Les résultats `SimulationResult` et `DynamicResult` ne sont pas interchangeables : les analyses dynamiques doivent utiliser un adaptateur ou des KPI dédiés.

Le schéma et les choix précédents documentent surtout l'architecture initiale. Depuis la livraison V7, la scène 2D et les espaces d'analyse sont intégrés dans `app.py`. Les paragraphes précédents décrivent les choix historiques de conception.
