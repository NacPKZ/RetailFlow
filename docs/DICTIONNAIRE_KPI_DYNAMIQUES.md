# Dictionnaire des KPI dynamiques — RetailFlow

## Source et périmètre

Les résultats proviennent de `DynamicSimulationEngine.run(config, options)` et sont analysés
par `DynamicKPICalculator`. Le calculateur historique `KpiCalculator` n'est pas utilisé : il
attend un `SimulationResult` FIFO et non un `DynamicResult`.

Tous les temps sont exprimés en minutes simulées. Les données clients et les durées de service
sont synthétiques. Les calculs sont effectués après l'exécution complète de la simulation ; ils
ne constituent pas un flux live.

## Populations

- **Arrivés** : tous les objets clients de `DynamicResult.customers`.
- **Servis** : clients possédant `service_start` et `departure_time`.
- **Abandonnés** : clients possédant `abandoned_at`.
- **Présents à t** : clients en attente plus clients en cours de service, reconstruits depuis les événements.

Une attente servie est `service_start - arrival_time`. Le temps avant abandon est
`abandoned_at - arrival_time`. Ces deux valeurs ne sont jamais fusionnées dans les KPI d'attente
servie.

## Indicateurs

| Indicateur | Formule | Unité | Population / fenêtre | Si indisponible |
|---|---|---|---|---|
| Arrivées | Nombre de clients | clients | Tous les clients du résultat | 0 si population vide |
| Servis | Nombre de clients avec début et départ de service | clients | Clients servis | 0 si aucun servi |
| Abandons | Nombre de clients avec `abandoned_at` | clients | Clients abandonnés | 0 si aucun abandon |
| Attente moyenne | Moyenne de `service_start - arrival_time` | min | Servis uniquement | `None` si aucun servi |
| Médiane d'attente | Médiane de `service_start - arrival_time` | min | Servis uniquement | `None` si aucun servi |
| P90 / P95 | Quantiles linéaires inclusifs des attentes servies | min | Servis uniquement | `None` si aucun servi |
| Attente maximale | Maximum de `service_start - arrival_time` | min | Servis uniquement | `None` si aucun servi |
| Durée moyenne de service | Moyenne de `service_duration` | min | Servis uniquement | `None` si aucun servi |
| Temps total moyen dans le système | Moyenne de `departure_time - arrival_time` | min | Servis uniquement | `None` si aucun servi |
| Temps total cumulé dans le système | Somme de `departure_time - arrival_time` | client-min | Servis uniquement | `None` si aucun servi |
| Taux d'abandon | Abandons / arrivées | proportion (0–1) | Tous les arrivés, simulation complète | `None` si 0 arrivée |
| Temps moyen avant abandon | Moyenne de `abandoned_at - arrival_time` | min | Abandonnés uniquement | `None` si aucun abandon |
| Débit | Servis / (dernier terminal - première arrivée) | clients/min | Servis, sur la fenêtre d'observation clients | `None` si durée nulle ou inconnue |
| Longueur de file | Nombre de clients en attente à t, caisse par caisse | clients | État reconstruit à t, service exclu | 0 si la file est vide |
| Occupation d'une caisse | Temps de service effectif / temps disponible effectif | proportion (0–1) | Chaque caisse, de t=0 au dernier départ/abandon | `None` si temps disponible nul |
| Conservation des flux | Arrivés = terminés + abandonnés + en attente + en service | clients | À chaque instant observé | Indicateur booléen de validation |

## Quantiles

Les percentiles P90 et P95 utilisent `statistics.quantiles` avec `method="inclusive"`, soit une
interpolation linéaire inclusive. Pour un seul client servi, le quantile est égal à son attente.

## Reconstruction temporelle

Les événements sont rejoués dans l'ordre fourni par `DynamicResult.events`. Ils ne sont pas
triés à nouveau : l'ordre des événements simultanés est conservé. Une photographie à l'instant
t est prise après le traitement de tous les événements ayant exactement cet horodatage.

La file contient uniquement les clients en attente ; le client en service est compté à part.
Les événements d'arrivée, d'entrée en file, de début de service, de départ, d'abandon, de
changement de file et d'ouverture/fermeture mettent à jour l'état reconstitué. Les champs
optionnels sont contrôlés avant d'être utilisés ; quand un événement n'identifie pas sa caisse,
le résultat client peut fournir sa caisse finale pour les événements d'affectation.

À chaque photographie :

`arrivés = départs après service + abandons + clients en attente + clients en service`

## Convention d'occupation et fermeture

Le numérateur est la somme des durées de service réellement effectuées sur la caisse.
Le temps ouvert est reconstruit à partir de l'état initial et des événements
`register_opened` / `register_closed`, dans la fenêtre allant de t=0 au dernier départ ou
abandon.

Le moteur laisse terminer un service déjà commencé lorsque la caisse ferme. Pour ne pas
produire un taux supérieur à 100 % par simple incohérence de dénominateur, le temps disponible
effectif est l'union des périodes d'ouverture et des intervalles de service déjà commencés qui
se prolongent après la fermeture. Aucune nouvelle prise en charge n'est supposée sur une caisse
fermée.

## Comparaison et recommandation

Pour chaque n de 1 à 5, le moteur dynamique est exécuté avec les mêmes paramètres et la même
graine. `CustomerGenerator` initialise un `random.Random(seed)` dédié à chaque appel, génère
d'abord les arrivées puis les durées de service ; le code de comparaison contrôle que la
signature des clients est identique pour chaque n.

Une comparaison est refusée si la graine est `None` ou si un calendrier de changements de
caisses est fourni. Un calendrier identique peut ouvrir ou fermer un numéro de caisse différent
selon la capacité initiale et rendrait l'interprétation par nombre initial de caisses ambiguë.

La recommandation retient le plus petit n dont l'attente moyenne des clients servis est
inférieure ou égale au seuil. Une moyenne indisponible n'est pas conforme. Si aucun n ne respecte
le seuil, le message affiché est `aucune configuration conforme`. Le taux d'abandon et les gains
marginaux sont présentés en complément ; ils ne changent pas la règle de sélection. Cette règle
ne modélise pas le coût du personnel et n'est pas une optimisation économique exhaustive.

## Colonnes des exports

| Fichier / onglet | Colonnes principales | Unités / remarques |
|---|---|---|
| `clients.csv` / Clients | `customer_id`, arrivée, caisse, durée de service générée, début, départ, abandon, issue, attente servie, temps avant abandon, temps total | Temps en min ; durée générée conservée même si le client abandonne, mais la durée moyenne de service ne porte que sur les servis |
| `evenements.csv` / Événements | ordre d'origine, temps, type, client, caisse source/cible, position | Temps en min ; ordre original conservé |
| `caisses.csv` / Caisses | servis, attente moyenne, temps de service, temps ouvert, temps disponible, occupation, pic de file | Temps en min ; occupation en proportion 0–1 |
| `kpi.csv` / Résumé KPI | indicateur, valeur, unité, population, formule, fenêtre, méthode | `None` exporté comme cellule vide |
| `comparaison.csv` / Comparaison | nombre de caisses, servis, abandons, attente, P95, gains absolu et relatif | Temps en min ; taux en proportion 0–1 |
| Paramètres | graine, hypothèses, seuil, version déclarée ou non, date de génération | La version du moteur n'est pas inventée si elle n'existe pas dans le dépôt |
