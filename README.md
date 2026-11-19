# RetailFlow

**Simulation interactive et aide à la décision pour les files d'attente en supermarché**

Projet universitaire réalisé en Master 2 Big Data, Analyse & Business Intelligence (BIDABI), à l'Université Sorbonne Paris Nord. RetailFlow étudie le compromis entre temps d'attente, qualité de service et mobilisation des caisses à partir de **données synthétiques**.

**[Accéder à l'application Streamlit](https://retailflow-nacpkz.streamlit.app/)** | [Guide de démonstration](docs/SOUTENANCE.md) | [Méthodologie et validation](docs/RETAILFLOW_V7.md)

![Capture réelle de RetailFlow déployé](https://raw.githubusercontent.com/NacPKZ/RetailFlow/feature/retailflow-v7-final/docs/validation_v7/retailflow_public.jpg)

## Problématique

Combien de caisses faut-il mobiliser pour limiter l'attente des clients sans augmenter inutilement les coûts ? RetailFlow permet de **simuler**, **observer**, **intervenir** et **comparer** plusieurs configurations. Il s'agit d'un prototype pédagogique, non d'un système calibré sur les données d'un magasin réel.

## Parcours dans l'application

| Espace | Utilité |
| --- | --- |
| **Accueil** | Comprendre le problème, la démarche et les limites |
| **Simulation** | Observer les files en 2D, piloter la lecture et intervenir sur les caisses ou les clients |
| **Analyses** | Explorer les indicateurs, les distributions et les évolutions des files |
| **Optimisation** | Comparer plusieurs capacités et le compromis coût/service |
| **Méthodologie** | Comprendre les hypothèses, le calcul et la reproductibilité |

La scène 2D affiche une ligne par caisse, jusqu'à six clients visibles, puis un compteur de surplus. Tous les clients restent présents dans le modèle. Le lecteur propose notamment pause, accélération, zoom, mini-carte, suivi et inspection des clients. Les ouvertures, fermetures et réaffectations sont validées par le moteur Python.

## Fonctionnement technique

RetailFlow conserve **deux moteurs complémentaires**, dont les résultats ne doivent pas être confondus :

- **Moteur historique** (`queuesmart/simulation/engine.py`) : simulation FIFO, stratégies d'affectation, analyses et comparaisons historiques. Il ne modélise ni abandons ni changements de file.
- **Moteur dynamique** (`queuesmart/simulation/dynamic.py`) : simulation à événements discrets avec patience, abandons, changements de file, ouverture et fermeture des caisses. Son journal horodaté pilote la scène JavaScript.

**Python** calcule les événements et les résultats ; **JavaScript/Canvas** anime leur représentation ; **Streamlit** rassemble les contrôles, analyses et décisions. La vitesse d'animation ne modifie pas les calculs. Le package Python conserve son nom historique `queuesmart` pour préserver la compatibilité.

### Indicateurs et décision

Les analyses comprennent, selon le moteur utilisé, l'attente moyenne, les percentiles, les abandons, le niveau de service, l'occupation, le débit et la congestion. Dans le laboratoire dynamique, le niveau de service est rapporté à **tous les arrivants**, abandons compris. Les percentiles d'attente des servis ne représentent pas les abandons.

Le laboratoire compare de **1 à 5 caisses**, sur **5, 10 ou 20 graines** communes entre capacités. Il sélectionne le coût moyen minimal parmi les configurations qui respectent la cible sur chaque tirage testé ; si aucune ne convient, il ne produit pas de recommandation. Les coûts de personnel et d'abandon sont **des hypothèses ajustables**, pas des coûts observés. Les intervalles min/max ne constituent pas des intervalles de confiance.

## Démonstration reproductible

Le préréglage **Soutenance reproductible** utilise 110 clients, 60 minutes d'arrivées, un service moyen de 1,7 minute, deux caisses initiales et la graine 42. La patience de 12 minutes, les abandons et le rééquilibrage sont activés. Le bouton **Voir le pic** permet d'atteindre rapidement une situation de congestion.

La démonstration recommandée : observer le pic, ouvrir une caisse, réaffecter un client, comparer avec le témoin, puis examiner une recommandation du laboratoire. Les cinq scénarios calculés et leurs paramètres sont conservés dans [`docs/demonstration/`](docs/demonstration/). Le [guide de soutenance](docs/SOUTENANCE.md) propose un déroulé de cinq minutes et les questions du jury.

## Installation locale

Prérequis : **Python 3.11+**, Node.js pour les tests JavaScript.

```bash
git clone https://github.com/NacPKZ/RetailFlow.git
cd RetailFlow
python -m venv .venv
# Activer l'environnement virtuel selon votre système
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

**Important :** la version déployée se trouve actuellement sur la branche `feature/retailflow-v7-final`, pas sur `main`. Pour exécuter la version présentée dans ce README après clonage, utiliser `git switch feature/retailflow-v7-final` avant l'installation. L'application publique est configurée sur cette branche. Le point d'entrée officiel est `app.py` ; `dynamic_demo.py` reste un banc d'essai historique.

## Tests et qualité

```bash
python -m pytest -q
npm run test:scene
git diff --check
```

La livraison documente **287 tests Python réussis**, **trois suites JavaScript réussies** et une **GitHub Actions au vert**. Les tests portent notamment sur FIFO, conservation des clients, interventions, cohérence des KPI, comparaisons appariées, scène et exports. Voir [validation détaillée](docs/RETAILFLOW_V7.md) et [contrôle du déploiement](docs/DEPLOIEMENT.md). Ces résultats ne constituent pas une garantie d'absence de bugs.

## Architecture

```text
app.py                    Application Streamlit officielle
queuesmart/
  simulation/             Moteurs historique et événementiel
  analytics/              KPI, comparaisons et laboratoire de décision
  scene/                  Géométrie et chronologie
  ui/                     Interfaces Streamlit
frontend_studio/          Scène interactive JavaScript / Canvas
tests/                    Tests Python et JavaScript
scripts/                  Reproduction et benchmarks
docs/                     Méthodologie, validations et soutenance
.streamlit/               Configuration de l'application
```

## Documentation

| Document | Contenu |
| --- | --- |
| [Méthodologie et validation finale](docs/RETAILFLOW_V7.md) | Hypothèses, KPI, limites, architecture et contrôles |
| [Déploiement](docs/DEPLOIEMENT.md) | Application publique et vérifications réelles |
| [Soutenance](docs/SOUTENANCE.md) | Pitchs, plan des douze diapositives et démonstration |
| [Conception](docs/conception.md) | Architecture et responsabilités |
| [Moteurs](docs/moteur.md) | Hypothèses et règles de simulation |
| [Scène 2D](docs/SCENE_2D.md) | Fonctionnement de la visualisation |
| [Résultats reproductibles](docs/demonstration/scenarios.json) | Paramètres et résultats des scénarios |

Les documents V1 à V6.1 restent disponibles dans `docs/` comme **historique de développement** ; ils ne décrivent pas nécessairement le comportement final.

## Limites et perspectives

- Données synthétiques, sans calibration sur un supermarché réel.
- Arrivées et durées de service générées selon les hypothèses du simulateur.
- Coûts hypothétiques, sans chiffre d'affaires ni marge observés.
- Courses en rayons, scan et paiement visuels partiellement illustratifs ; pas de simulation physique de collisions.
- Projection de file à cinq minutes fondée sur une extrapolation simple, pas sur un modèle prédictif validé.
- Contrôle navigateur réalisé sur ordinateur ; tests mobiles et audit exhaustif d'accessibilité non documentés.
- Les exports PNG et JSON de scène n'ont pas été vérifiés de bout en bout dans le navigateur lors du dernier contrôle.

RetailFlow constitue un **outil d'expérimentation et d'aide à la réflexion**, pas une recommandation opérationnelle garantie.

## Équipe et contributions

Projet collectif de **quatre étudiants**. Les contributions individuelles doivent être présentées conformément au travail réellement réalisé et à l'historique Git, sans attribution artificielle. La [PR de livraison](https://github.com/NacPKZ/RetailFlow/pull/4) conserve la traçabilité des changements et reste soumise à revue avant fusion dans `main`.
