# QueueSmart

**QueueSmart aide le responsable d'un supermarché à décider combien de caisses ouvrir, en
simulant les files d'attente selon l'affluence.**

Si le magasin ouvre trop peu de caisses, les clients attendent. S'il en ouvre trop, le
personnel est sous-utilisé. QueueSmart simule un supermarché (1 à 8 caisses) dans trois
scénarios (heures creuses, heures normales, heure de pointe). Il mesure les temps d'attente
et **recommande le nombre de caisses** à ouvrir. Il mesure aussi le gain apporté par un
**écran client** qui affiche l'attente estimée à chaque caisse.

Les données sont générées en Python : pas de données réelles, pas d'API, pas de base de données.

*Projet du cours « Programmation épurée (Clean Code) », Master 2 BIDABI.*

---

## Fonctionnalités

L'application Streamlit comporte une barre latérale et trois onglets.

- **Barre latérale** : scénario prédéfini, puis ajustements (nombre de clients, durée
  d'arrivée, nombre de caisses, temps moyen de passage, comportement des clients, graine
  aléatoire). Les saisies incohérentes affichent un message clair, sans traceback.
- **Magasin 2D** : vue du dessus animée (lecture/pause et curseur de temps). On y voit les
  caisses avec leur attente estimée, et les clients colorés selon leur attente : vert,
  orange au-delà de la moitié du seuil de 5 min, rouge au-delà du seuil. On peut **suivre
  un client**, qui est alors entouré.

  ![Magasin 2D](docs/captures/magasin_2d.png)

- **Écran client** : panneau « temps d'attente estimé » par caisse à un instant choisi, avec
  la caisse conseillée mise en avant, et le parcours d'un client (arrivée, caisse, début,
  départ, attente).

  ![Écran client](docs/captures/ecran_client.png)

- **Dashboard responsable** :
  - indicateurs : attente moyenne, p90, attente maximale, part des clients au-delà de 5 min, occupation ;
  - **recommandation du nombre de caisses** (courbe du p90 selon le nombre de caisses, avec la cible) ;
  - graphiques : histogramme des attentes, attente selon l'heure d'arrivée, occupation par caisse ;
  - **gain apporté par l'écran client** (comparaison des comportements « file la plus courte »
    et « attente estimée minimale ») ;
  - comparaison des trois scénarios.

  ![Dashboard](docs/captures/dashboard.png)

### Deux comportements de client

| Comportement | Ce que fait le client |
|---|---|
| `shortest_queue` (« File la plus courte ») | il compte les personnes et va à la file la plus courte, comme dans la réalité |
| `least_wait` (« Attente estimée minimale ») | il suit l'écran client et va à la caisse dont l'attente estimée est la plus faible |

Exemple (graine 42, heure de pointe, 5 caisses) : avec l'écran, l'attente moyenne passe de
2,25 min à 1,91 min, et l'attente maximale de 10,2 min à 4,4 min.

---

## Prérequis

- **Python 3.11 ou plus récent** (le projet a été développé sous Python 3.12).
- `pip` (fourni avec Python).

## Installation

Depuis la racine du dépôt :

```bash
# 1. Créer un environnement virtuel
python -m venv .venv

# 2. L'activer
#    Windows (PowerShell) :
.venv\Scripts\Activate.ps1
#    macOS / Linux :
source .venv/bin/activate

# 3. Installer les dépendances (versions épinglées)
pip install -r requirements.txt
```

## Exécution

```bash
# Application web (s'ouvre sur http://localhost:8501)
streamlit run app.py

# Démo du moteur dans le terminal (résumé des 3 scénarios)
python -m scripts.demo_moteur
```

## Tests et qualité

```bash
pytest                                   # tous les tests (~1 min, dont le test de bout en bout de l'appli)
pytest --cov=queuesmart                  # avec la couverture de code
ruff check .                             # analyse statique (style, imports, bugs fréquents)
```

Les tests couvrent les règles métier et les invariants du moteur, les KPI sur des cas
calculés à la main, la recommandation, la logique pure de l'interface, et un test de bout en
bout de l'application Streamlit (`streamlit.testing`) sur les 3 scénarios × 2 comportements.
La couverture est de 100 % hors `ui/` et de 99 % au total.

---

## Architecture et choix techniques

```
app.py                  assemblage Streamlit, aucune logique métier
queuesmart/
├── config.py           constantes + ScenarioConfig validé + scénarios prédéfinis
├── exceptions.py       erreurs métier typées (QueueSmartError, …)
├── domain/             Customer, CheckoutRegister
├── simulation/         CustomerGenerator, stratégies, SimulationEngine, SimulationResult
├── analytics/          KpiCalculator, comparaisons, RegisterRecommender
└── ui/                 logique pure (store_layout, client_board) + rendu Streamlit
tests/                  un fichier de test par module
scripts/demo_moteur.py  démo terminal
docs/                   conception, moteur, exemples Clean Code
```

Les dépendances vont dans un seul sens : `ui → analytics → simulation → domain → config`.
Seul `ui/` importe Streamlit.

Stack : Python, Streamlit, Plotly, pandas. Le moteur n'utilise que la bibliothèque standard.
Outils : pytest, pytest-cov, ruff.

Pour aller plus loin :

- [docs/conception.md](docs/conception.md) : classes, responsabilités, relations, **diagramme UML** et choix de conception ;
- [docs/moteur.md](docs/moteur.md) : modèle d'arrivées, comportements, invariants, erreurs ;
- [docs/clean_code_examples.md](docs/clean_code_examples.md) : exemples avant/après.

### Comment est calculée la recommandation ?

Pour chaque nombre de caisses de 1 à 8, on lance 20 simulations avec des graines différentes
et on calcule les KPI sur l'ensemble des clients. On retient le **plus petit** nombre de
caisses qui respecte la cible de service : **90 % des clients attendent au plus 5 min** et
**au plus 10 % dépassent 5 min**. Si aucun nombre ne convient, l'application le signale.
Avec la graine 42, on obtient 3 caisses aux heures creuses (2 avec l'écran client), 4 aux
heures normales et 6 à l'heure de pointe.

---

## Limites et pistes d'évolution

- **Abandon de file** : tous les clients attendent jusqu'au bout ; on pourrait ajouter un seuil de patience.
- **Changement de file** : un client ne change jamais de file une fois placé.
- **Affluence variable** : les arrivées sont uniformes sur la fenêtre ; une affluence qui
  varie dans la journée (pics à midi et à 18 h) serait plus réaliste.
- **Estimation de l'écran** : l'écran connaît parfaitement la durée de passage de chaque client.
- Caisses rapides ou automatiques, coût du personnel dans la recommandation.
- Extension facultative en Scala.

## Répartition des tâches

| Membre | Périmètre |
|---|---|
| Billal | Moteur : configuration, exceptions, domaine, génération, stratégies, moteur, résultat, tests, `docs/moteur.md` |
| Yanis | Animation 2D : `StoreLayout` (logique pure et tests), rendu Plotly animé, suivi d'un client |
| Nithilan | Barre latérale et validation, écran client (`client_board`, `client_screen`), assemblage `app.py`, tests |
| Can | KPI, comparaisons, recommandation, dashboard, README, `docs/conception.md`, présentation |
