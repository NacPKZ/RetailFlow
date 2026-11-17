# RetailFlow | Documentation des moteurs de simulation

Le moteur historique (`queuesmart/config.py`, `exceptions.py`, `domain/` et `simulation/`) n'utilise que la
bibliothèque standard Python. Il ne dépend ni de Streamlit, ni de pandas, ni de Plotly.

## Unités

Tous les temps sont en **minutes (float)** depuis l'ouverture du magasin (t = 0).

## Déroulement d'une simulation

```
ScenarioConfig ──► CustomerGenerator.generate() ──► clients triés par arrivée
                                                        │
              pour chaque client, dans l'ordre d'arrivée │
                                                        ▼
           AssignmentStrategy.choose(caisses, heure d'arrivée) ──► CheckoutRegister.serve(client)
                                                        │
                                                        ▼
                                              SimulationResult (immuable)
                                     snapshot_at(t) / timeline(pas) / customer(id)
```

1. **Génération** (`CustomerGenerator`)
   - Arrivées : `customer_count` instants tirés uniformément sur `[0, arrival_window_min]`,
     puis triés. C'est mathématiquement équivalent à un **processus de Poisson conditionné**
     au nombre d'arrivées : on fixe le nombre de clients et les instants sont « au hasard ».
   - Durées de passage : **loi gamma** de forme `SERVICE_TIME_SHAPE = 2` et de moyenne
     `mean_service_time_min` (échelle = moyenne / forme). La loi gamma est positive et
     asymétrique : la plupart des clients passent vite, quelques gros chariots prennent
     longtemps. Un plancher `MIN_SERVICE_TIME_MIN = 0,3 min` évite les durées irréalistes.
   - Reproductibilité : un `random.Random(seed)` dédié est créé à chaque `generate()`.
     On n'utilise jamais le `random` global. Même graine, mêmes clients.
2. **Affectation** : les clients sont traités dans l'ordre d'arrivée. La stratégie choisit
   une caisse d'après l'état des caisses **à l'instant d'arrivée**.
3. **Service** (`CheckoutRegister.serve`) : début = `max(arrivée, fin du client précédent)`.
   La file est FIFO.
4. **Résultat** : `SimulationResult` regroupe la config, le nom de la stratégie, les clients
   et les caisses. Il sait reconstituer l'état du magasin à n'importe quel instant.

Pourquoi le moteur **historique** n'est-il pas une simulation « à événements discrets » avec une horloge ? Parce que,
dans une file FIFO sans abandon ni changement de file, l'heure de début de service d'un client
se calcule **dès son arrivée**. Une seule boucle sur les clients suffit, ce qui est plus simple
à lire, à tester et à expliquer.

## Les deux comportements de client

| Nom | Libellé | Règle | Égalité |
|---|---|---|---|
| `shortest_queue` | File la plus courte | minimise `queue_length_at(t)` (clients présents, service compris) | plus petit numéro |
| `least_wait` | Attente estimée minimale (écran client) | minimise `estimated_wait_at(t)` | plus petit numéro |

`estimated_wait_at(t)` = temps restant avant que la caisse ait servi tous les clients **déjà
arrivés** à t. L'écran ne connaît pas l'avenir, mais il connaît le travail restant de chaque
client. **Hypothèse** : l'estimation est parfaite, comme si elle était calculée à partir du
nombre d'articles. Les deux comportements divergent quand une file courte contient un gros
chariot (voir `tests/test_strategies.py`).

## Invariants garantis (et testés dans `tests/test_engine.py`)

- aucun service ne commence avant l'arrivée du client (`InvalidAssignmentError` sinon) ;
- pas de chevauchement sur une caisse : chaque service commence après la fin du précédent ;
- tout le monde est servi ;
- à tout instant : `non arrivés + présents + partis = total`.

## Erreurs

| Exception | Quand ? |
|---|---|
| `InvalidScenarioError` | paramètres de `ScenarioConfig` incohérents (message en français) |
| `InvalidAssignmentError` | client affecté deux fois, ou servi avant son arrivée |
| `CustomerNotServedError` | `service_end` ou `wait_time` demandés avant l'affectation |
| `UnknownCustomerError` | `SimulationResult.customer(id)` avec un identifiant absent |
| `UnknownStrategyError` | `build_strategy` avec un nom inconnu |
| `ValueError` | argument utilitaire invalide (pas de temps <= 0, liste de caisses vide…) |

Toutes les erreurs métier héritent de `QueueSmartError`.

## Scénarios prédéfinis

| Scénario | Clients | Fenêtre | Passage moyen | Caisses | Charge (clients/min × passage) |
|---|---|---|---|---|---|
| Heures creuses | 50 | 60 min | 2,0 min | 3 | 1,7 caisse occupée en moyenne |
| Heures normales | 90 | 60 min | 2,0 min | 4 | 3,0 |
| Heure de pointe | 145 | 60 min | 2,0 min | 5 | 4,8 |

La « charge » est le nombre moyen de caisses nécessaires. Il faut toujours en ouvrir davantage
pour absorber les arrivées groupées, d'où les recommandations de 3, 4 et 6 caisses.

## Démo terminal

```bash
python -m scripts.demo_moteur
```

Résultat avec la graine 42 :

```
Scénario         Comportement     Caisses Clients  Attente moy.  Attente max     Fin
------------------------------------------------------------------------------------
Heures creuses   shortest_queue         3      50          0.38         5.56    60.1
Heures creuses   least_wait             3      50          0.18         1.48    60.1
Heures normales  shortest_queue         4      90          0.79        10.54    63.8
Heures normales  least_wait             4      90          0.47         2.81    63.8
Heure de pointe  shortest_queue         5     145          2.25        10.23    65.3
Heure de pointe  least_wait             5     145          1.91         4.38    64.1
```

L'écran client réduit l'attente moyenne et, surtout, l'attente maximale.

## Limites connues

- pas d'abandon de file, ni de changement de file une fois le client placé ;
- affluence uniforme sur la fenêtre (pas de pic à l'intérieur de l'heure) ;
- l'écran client estime parfaitement les durées de passage ;
- pas de caisse rapide (« moins de 10 articles ») ni de caisse automatique.


## Extension : moteur événementiel dynamique

Le module `queuesmart/simulation/dynamic.py` ajoute une seconde implémentation, indépendante du moteur FIFO historique. Il prend en charge 1 à 5 caisses, les changements de file, les abandons selon une patience configurable et les ouvertures/fermetures programmées. Il produit un `DynamicResult` avec `events` et `customers`.

Le banc d'essai est `dynamic_demo.py`. L'interface principale `app.py` repose encore principalement sur le moteur historique. Les invariants de cette documentation concernant « tous les clients servis » s'appliquent **uniquement au moteur historique** : dans le moteur dynamique, certains clients peuvent abandonner.

Pour les contrats de données et limites d'intégration, voir [la transmission V2](TRANSMISSION_EQUIPE_V2.md).
