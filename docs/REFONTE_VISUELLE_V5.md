# RetailFlow : intégration et refonte visuelle V5

Date : 18 novembre 2026.

## Constat et corrections

| Défaut confirmé dans le dépôt ou les demandes visibles | Correction |
|---|---|
| Scène 2D sur une branche distincte, absente de l’application principale | Intégration de la contribution `feature/scene-2d-turbo`, accessible dans Simulation |
| Démo technique avec tableaux et types d’événements anglais visibles immédiatement | Vue centrée sur la scène, analyses au choix, journal filtrable avec libellés français |
| Iframe de hauteur fixe 1 100 px | Hauteur ajustée au contenu, scène plafonnée à 480 px, disposition adaptée aux petits écrans |
| Lecture lente et peu guidée | x20, prochain événement, message de départ, sélection d’un client et raccourcis |
| Compteur de présents fondé sur les sprites visibles, incluant les trajets de sortie | Compteur reconstitué à partir des arrivées, sorties et abandons Python |
| Grands panneaux et animations décoratives cumulées | CSS regroupé, cartes compactes, animations courtes et mouvement réduit respecté |
| Caisses traitées comme une variable numérique continue | Couleurs catégorielles stables de la caisse 1 à la caisse 8 |
| Chronologie représentée par des points | Barres de service placées aux minutes exactes, avec leur durée réelle |
| Graphiques nombreux mais répétitifs | Vues par question : flux, attentes, caisses, parcours et décision |
| Comparaison dépendant d’une seule graine | 5, 10 ou 20 graines communes aux configurations |
| Résultat calculé encore affiché après changement de paramètres | Signature du scénario et invalidation des anciennes comparaisons |
| Risque de présenter les abandons comme une amélioration de l’attente | Statuts distincts et niveau de service rapporté à tous les arrivants |
| Bornes de seuil et attentes identiques mal représentables | Tests sur zéro, exactement 5 min, histogramme par statut de seuil et ECDF avec valeurs regroupées |

La conversation partagée affiche les demandes de l’utilisateur, mais pas les réponses
d’audit dans l’environnement de lecture utilisé. Cette liste repose donc sur les
demandes lisibles et les défauts vérifiés dans les sources. Elle ne prétend pas
reproduire intégralement un audit qui n’a pas pu être lu.

## Organisation

- `queuesmart/analytics/visual_data.py` : données et calculs de flux, sans Streamlit.
- `queuesmart/ui/charts.py` : fabriques Plotly communes.
- `queuesmart/ui/presentation.py` et `assets/retailflow.css` : présentation partagée.
- `queuesmart/ui/dynamic_view.py` : scène, options et analyses du résultat dynamique.
- `frontend_2d/` : lecteur de la contribution 2D, enrichi sans décision métier en JavaScript.

Les graphiques historiques utilisent le moteur FIFO ; les graphiques sous la scène
utilisent son propre résultat dynamique. Le comportement historique de la barre latérale
ne pilote pas le choix dynamique, qui utilise l’attente estimée.

La scène conserve 5 caisses, le comparateur historique peut en tester 8. Une saisie
explicite permet de choisir la capacité de la scène lorsque celle de l’analyse dépasse 5.
Les changements de caisse sont programmés avant calcul et ne sont pas des commandes
sur un magasin en temps réel.

## Validation

- 213 tests Python réussis avec les dépendances épinglées du dépôt.
- Tests supplémentaires : bilan des arrivants à chaque événement, événements simultanés,
  abandons, caisses inutilisées, seuil exact, ECDF, absence de données dans la carte,
  comparaison reproductible, vues et filtres, données périmées, cas d’un client unique.
- `node tests/scene_controls.cjs` : pause/reprise, prochain événement, retours arrière,
  x20, files par caisse et compteurs vérifiés sans navigateur.
- Ruff passe sur tous les fichiers Python créés ou modifiés par cette refonte.
- L’analyse Ruff de tout le dépôt signale encore 102 diagnostics dans des modules
  préexistants hors de cette refonte, principalement des lignes trop longues.

Le navigateur Chromium local ne démarre pas dans cet environnement (création de socket
refusée). Aucun contrôle visuel bureau/mobile ni capture du rendu final n’a donc été
validé. Les tests Streamlit vérifient le calcul et la construction des pages, pas leur
apparence dans un navigateur. Un contrôle visuel reste à réaliser avant fusion.

## Exécution

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

```powershell
python -m pytest -o addopts='' -q
node tests/scene_controls.cjs
```
