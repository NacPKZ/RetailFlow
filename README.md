# RetailFlow

**Simulation et optimisation des files d'attente en supermarché**

Projet universitaire de Master 2 BIDABI (Big Data, Analyse & Business Intelligence), consacré à la simulation de flux de clients, à la mesure de la qualité de service et à l'aide à la décision sur le nombre de caisses.

> **État du projet : version de travail collaborative.** L'interface analytique et le moteur FIFO historique fonctionnent dans `app.py`. Le moteur événementiel dynamique est disponible dans `dynamic_demo.py`. La scène pixel art et le dashboard dynamique définitif restent à intégrer.

## Le problème étudié

Un magasin doit limiter les temps d'attente sans mobiliser inutilement trop de caisses. RetailFlow permet d'explorer ce compromis dans des **scénarios synthétiques**, reproductibles grâce à une graine aléatoire. Aucun jeu de données clients réel n'est utilisé.

## Deux moteurs complémentaires

| | Moteur historique | Moteur dynamique |
|---|---|---|
| Entrée | `queuesmart/simulation/engine.py` | `queuesmart/simulation/dynamic.py` |
| Interface | `app.py` | `dynamic_demo.py` |
| Files FIFO | Oui | Oui |
| Stratégies | File la plus courte, attente estimée minimale | Choix de caisse avec réévaluation |
| Changement de file | Non | Oui |
| Abandon selon la patience | Non | Oui |
| Ouverture et fermeture programmées | Non | Oui, de 1 à 5 caisses |
| Statut | Interface principale | Banc d'essai technique |

Le moteur historique calcule les affectations et permet les comparaisons de scénarios. Le moteur dynamique produit des **événements horodatés** (`customer_arrived`, `queue_joined`, `service_started`, `queue_switched`, `customer_abandoned`, `register_opened`, `register_closed`, `customer_departed`). Ces événements doivent alimenter la future animation 2D, sans recalculer les décisions métier dans le navigateur.

## Application et analyses

L'interface RetailFlow propose quatre espaces : **Vue d'ensemble**, **Simulation**, **Analyse** et **Comparaison**. Elle rassemble des KPI, des distributions d'attente, des nuages de points, des analyses par caisse et des exports. Ces résultats concernent principalement **le moteur historique**. Les abandons et changements de file ne doivent pas être attribués à ces graphiques.

Le projet conserve deux approches de recommandation distinctes :
- une recommandation historique fondée sur le 90e percentile (P90) et un seuil de service ;
- un optimiseur expérimental fondé sur l'attente moyenne (`queuesmart/analytics/mean_wait_optimizer.py`), actuellement appliqué au moteur historique.

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
ruff check .
```

Les tests couvrent la génération, les stratégies, les invariants de simulation, les événements, les recommandations et l'interface Streamlit. **La suite locale a été signalée comme réussie le 17 novembre 2026 après adaptation des tests d'interface** ; les contrôles visuels et l'intégration des modules des autres membres restent à réaliser.

## Architecture

```text
RetailFlow/
├── app.py                        Interface principale (moteur historique)
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
- `feature/simulation-2d` : scène animée, déplacements et files.
- `feature/dashboard-analytics` : indicateurs, comparaisons et exports.

Chaque membre travaille sur sa branche et propose une **Pull Request** vers `main`. Ne pas fusionner de changements sans exécuter les tests et vérifier les contrats de données.

## Contributions et attribution

La base initiale QueueSmart a été réalisée en équipe et a fourni le moteur FIFO, les stratégies, les KPI et une première interface. L'évolution RetailFlow comprend l'audit, le moteur événementiel, des tests additionnels, une nouvelle interface et les contrats de transmission. La scène 2D et le dashboard définitif sont des contributions séparées en cours. Pour une attribution individuelle précise, consulter l'historique Git et les Pull Requests plutôt que d'attribuer tout le code à une seule personne.

## Limites

Les données sont simulées, l'estimation d'attente peut exploiter une information parfaite sur les durées de service, et les résultats ne sont pas des prévisions opérationnelles pour un magasin réel. Le moteur dynamique est actuellement séparé de l'interface principale. Les ouvertures/fermetures y sont **programmées avant exécution**, non pilotées en direct depuis la scène. Le périmètre 1 à 5 caisses doit encore être harmonisé avec certains modules historiques pouvant aller jusqu'à 8.

**Technologies :** Python, Streamlit, pandas, Plotly, pytest, ruff.
