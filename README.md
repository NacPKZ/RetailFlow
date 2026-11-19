# RetailFlow V7.0 : Enterprise Edition

**Prototype universitaire d’aide à la décision, sans déploiement commercial revendiqué.**

**Simulation et optimisation des files d'attente en supermarché**

Projet universitaire de Master 2 BIDABI (Big Data, Analyse & Business Intelligence), consacré à la simulation de flux de clients, à la mesure de la qualité de service et à l'aide à la décision sur le nombre de caisses.

> **V7.0 :** une seule ligne par caisse (six clients visibles, surplus compté), centre de contrôle synchronisé, mini-carte et caméra bornée, suivi client, projection de tendance explicite, laboratoire dynamique coût / service sur plusieurs graines et dossier de décision exportable. [Guide et validation V7](docs/RETAILFLOW_V7.md). La vérification visuelle en navigateur de cette version reste à réaliser.

> **Finalisation V6.1 :** inspecteur temporel avec recherche, réaffectation par sélection, journal des décisions réellement appliquées, comparaison détaillée et mode soutenance reproductible. Voir [le bilan de validation](docs/FINALISATION_RETAILFLOW_V6_1.md).

> **Atelier interactif V6 :** scène en grande largeur et immersion, caisses cliquables, clients réaffectables à la souris, annulation et comparaison au témoin. Voir [le guide complet](docs/ATELIER_INTERACTIF_V6.md).

> **Version intégrée :** `app.py` donne accès aux analyses FIFO et à la scène pixel art dynamique dans l’espace Simulation. La scène et ses graphiques utilisent le même résultat Python. `dynamic_demo.py` reste un raccourci vers cette scène.

## Le problème étudié

Un magasin doit limiter les temps d'attente sans mobiliser inutilement trop de caisses. RetailFlow permet d'explorer ce compromis dans des **scénarios synthétiques**, reproductibles grâce à une graine aléatoire. Aucun jeu de données clients réel n'est utilisé.

## Deux moteurs complémentaires

| | Moteur historique | Moteur dynamique |
|---|---|---|
| Entrée | `queuesmart/simulation/engine.py` | `queuesmart/simulation/dynamic.py` |
| Interface | `app.py` | `app.py`, espace Simulation, ou `dynamic_demo.py` |
| Files FIFO | Oui | Oui |
| Stratégies | File la plus courte, attente estimée minimale | Choix de caisse avec réévaluation |
| Changement de file | Non | Oui |
| Abandon selon la patience | Non | Oui |
| Ouverture et fermeture programmées | Non | Oui, de 1 à 5 caisses |
| Statut | Analyse et comparaison | Scène intégrée avec indicateurs et exports |

Le moteur historique calcule les affectations et permet les comparaisons de scénarios. Le moteur dynamique produit des **événements horodatés** (`customer_arrived`, `queue_joined`, `service_started`, `queue_switched`, `customer_abandoned`, `register_opened`, `register_closed`, `customer_departed`). Ces événements alimentent la scène 2D. Les clics de caisse et réaffectations à la souris remontent au moteur Python, qui recalcule le futur avec la même clientèle. Le lecteur propose pause, reprise, zoom, immersion, repères et vitesses jusqu’à x50.

## Application et analyses

L'interface RetailFlow propose quatre espaces : **Vue d'ensemble**, **Simulation**, **Analyse** et **Comparaison**. Elle rassemble des KPI, des distributions d'attente, des nuages de points, des analyses par caisse et des exports. Ces résultats concernent principalement **le moteur historique**. Les abandons et changements de file ne doivent pas être attribués à ces graphiques.

Le **Laboratoire de décision**, sous la scène, compare désormais de 1 à 5 caisses avec le moteur dynamique. Il conserve patience, abandons et rééquilibrage, puis simule chaque capacité sur les mêmes 5, 10 ou 20 graines. Les coûts horaires et d’abandon sont des hypothèses modifiables. La recommandation retient le coût moyen minimal parmi les capacités respectant la cible dans chaque tirage, sans garantie future.

Le projet conserve également deux approches historiques distinctes :
- une recommandation historique fondée sur le 90e percentile (P90) et un seuil de service ;
- un optimiseur expérimental fondé sur l'attente moyenne (`queuesmart/analytics/mean_wait_optimizer.py`), actuellement appliqué au moteur historique.


### Graphiques et lecture des résultats

- Congestion calculée à chaque événement : clients en attente et en service.
- Nuages de points par caisse, palette catégorielle stable et détails au survol.
- Histogramme des attentes, seuil de 5 minutes et courbe de répartition cumulée.
- Charge des caisses, chronologie des services à leur durée réelle et carte des attentes par tranche.
- Analyse filtrable par caisse, avec message explicite si le filtre ne contient aucun client.
- Comparaison de 1 à 8 caisses sur 5, 10 ou 20 graines identiques entre capacités.
- Comparaison des comportements avec et sans écran, sans imposer un gain positif.
- Exports CSV pour Excel et JSON des paramètres. La barre Plotly permet l’export PNG et le zoom.

Le graphique de comparaison montre l’étendue observée des moyennes selon les graines,
qui n’est pas un intervalle de confiance. La cible combine P90 ≤ 5 min et au moins
90 % des attentes ≤ 5 min. Dans la scène dynamique, le niveau de service utilise tous
les arrivants comme dénominateur : un abandon reste un échec, même après une attente courte.

## Utiliser l’atelier

L’application démarre dans Simulation. Le bouton « Plein écran » agrandit le magasin ;
« Voir le pic » permet d’explorer rapidement sa congestion maximale. Cliquez une caisse
pour l’ouvrir ou la fermer. Glissez un client en file vers une caisse ouverte pour le
réaffecter. Une alternative clavier et tactile est disponible : recherchez son identifiant,
choisissez une caisse de destination et appuyez sur « Réaffecter ». Les sections Interventions et Journal permettent de comparer et exporter
l’expérience. Les réglages et situations d’affluence sont disponibles sous la scène. La mini-carte et le bouton « Cadrer les caisses » facilitent l’exploration. « Vue complète » affiche l’inspecteur ; « Focus magasin » agrandit la scène. Les animations décoratives peuvent être désactivées sans modifier le journal.

## Démonstration universitaire

Dans les réglages de l'atelier, choisissez **Soutenance reproductible** : 110 clients,
arrivées sur 60 min, service moyen 1,7 min, deux caisses initiales, graine 42.
Conservez patience 12 min, abandons et rééquilibrage activés. Activez **Mode soutenance**
pour parcourir situation, congestion, décision, comparaison et conclusion.
Le bouton « Voir le pic » évite une attente pendant l'oral.

Un résultat de secours et son CSV sont fournis dans `docs/validation_v6_1/`.
Pour les reproduire : `python scripts/prepare_soutenance.py`.
Le protocole de trois à cinq minutes et les limites figurent dans
[le bilan V6.1](docs/FINALISATION_RETAILFLOW_V6_1.md).

## Démarrage rapide

Prérequis : Python 3.11 ou version ultérieure (développement sous Python 3.12).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Depuis le dossier racine du dépôt, pour tester séparément le moteur dynamique :

```powershell
python -m streamlit run dynamic_demo.py
```

Sur macOS/Linux, l'activation est `source .venv/bin/activate`.

## Tests

```powershell
python -m pytest -q
python -m pytest --cov=queuesmart
node tests/scene_controls.cjs
npm run test:scene
ruff check app.py queuesmart/analytics/decision_lab.py queuesmart/ui/decision_lab.py queuesmart/ui/dynamic_view.py queuesmart/ui/studio_component.py queuesmart/scene/layout.py tests/test_decision_lab.py tests/test_decision_lab_ui.py
git diff --check
```

Les tests couvrent la génération, les stratégies, les invariants de simulation, les événements, les recommandations et l'interface Streamlit. La refonte du 18 novembre 2026 ajoute des tests des flux, des abandons, des seuils exacts, des filtres et de l’invalidation des résultats. Le lecteur JavaScript est vérifié avec `node tests/scene_controls.cjs` et `npm run test:scene`. Voir [le bilan de refonte](docs/REFONTE_VISUELLE_V5.md) pour le périmètre de validation et ses limites.

## Architecture

```text
RetailFlow/
├── app.py                        Interface principale, deux moteurs
├── dynamic_demo.py               Banc d'essai du moteur événementiel
├── queuesmart/                   Nom technique conservé du package Python
│   ├── config.py                 Paramètres et scénarios
│   ├── domain/                   Clients et caisses
│   ├── simulation/               Génération, FIFO, stratégies, événements, dynamique
│   ├── analytics/                KPI, comparaisons et optimisation
│   └── ui/                       Composants de présentation
├── tests/                        Tests automatisés
├── docs/                         Documentation et contrats d'intégration
└── requirements.txt
```

**Pourquoi le dossier `queuesmart` existe encore ?** RetailFlow est le nom du produit. `queuesmart` est le nom historique du package Python, maintenu temporairement pour ne pas casser les imports, scripts et tests. Son renommage technique nécessite une migration séparée et testée.

## Documentation

La V7 est décrite dans [RETAILFLOW_V7.md](docs/RETAILFLOW_V7.md), avec les fonctions livrées, les hypothèses, le déroulé de soutenance et les limites de validation.

| Document | Contenu |
|---|---|
| [Architecture et conception](docs/conception.md) | Modules, responsabilités et principes de conception |
| [Moteurs de simulation](docs/moteur.md) | Hypothèses, règles FIFO et limites |
| [Guide d'intégration des équipes](docs/TRANSMISSION_EQUIPE_V2.md) | Contrat dynamique prioritaire pour la 2D et l'analytics |
| [Contrat historique V1](docs/CONTRAT_INTEGRATION_V1.md) | Référence conservée pour la compatibilité |
| [Rapport de développement H1-H7](docs/RAPPORT_ETAPE_H1_H7.md) | Audit, extensions et vérifications |
| [Interface RetailFlow](docs/REFONTE_UI_RETAILFLOW_V4.md) | Historique des évolutions UI et limites |
| [Pratiques Clean Code](docs/clean_code_examples.md) | Exemples de refactorisation |

## Organisation GitHub

- `main` : version commune, fusion après revue.
- `feature/retailflow-v7-final` : V7, développée à partir du même commit que V6.1. La PR V7 cible V6.1 pour isoler ce complément ; aucune fusion automatique.
- `feature/simulation-2d` : scène animée, déplacements et files.
- `feature/dashboard-analytics` : indicateurs, comparaisons et exports.

Chaque membre travaille sur sa branche et propose une **Pull Request** vers `main`. Ne pas fusionner de changements sans exécuter les tests et vérifier les contrats de données.

## Contributions et attribution

La base initiale QueueSmart a été réalisée en équipe et a fourni le moteur FIFO, les stratégies, les KPI et une première interface. L'évolution RetailFlow comprend l'audit, le moteur événementiel, des tests additionnels, une nouvelle interface et les contrats de transmission. La scène 2D de la branche `feature/scene-2d-turbo` est intégrée en conservant sa contribution dans l’historique Git. Les graphiques partagés et les analyses dynamiques complètent cette intégration. Pour une attribution individuelle précise, consulter l'historique Git et les Pull Requests plutôt que d'attribuer tout le code à une seule personne.

## Limites

Les données sont simulées, l'estimation d'attente peut exploiter une information parfaite sur les durées de service, et les résultats ne sont pas des prévisions opérationnelles pour un magasin réel. Les deux moteurs sont accessibles dans la même interface, avec des périmètres explicitement indiqués. Les ouvertures/fermetures et réaffectations peuvent être déclenchées dans la scène ; elles sont validées et recalculées par le moteur Python. Le périmètre 1 à 5 caisses doit encore être harmonisé avec certains modules historiques pouvant aller jusqu'à 8.

**Technologies :** Python, Streamlit, pandas, Plotly, pytest, ruff.
