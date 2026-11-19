# RetailFlow | Scène 2D animée

Vue du dessus du supermarché, en pixel art, qui **rejoue** les événements du moteur
dynamique. La scène ne prend aucune décision métier : elle montre ce que le moteur a calculé.

## Lancer

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run dynamic_demo.py   # section « Scène 2D »
```

Commandes : lecture/pause, redémarrer, vitesse x1 à x5, curseur de temps. Cliquer sur un
client pour le suivre (cadre violet). À x1, 1 minute simulée dure 2 secondes.

## Pipeline

```
ScenarioConfig + DynamicOptions
  → DynamicSimulationEngine.run()            (moteur, inchangé)
  → DynamicResult.events
  → SceneTimelineBuilder.build()             (Python : rejoue chaque événement une fois)
  → SceneTimeline.to_dict()  → JSON
  → frontend_2d : échantillonne les trajectoires à l'instant affiché → Canvas
```

**Choix principal :** toute la logique « qui est où, à quel rang » est en Python et testée
avec pytest. Le JavaScript ne fait que dessiner et interpoler entre des images clés déjà
calculées. Conséquence : pause, reprise, vitesse et retour en arrière ne peuvent pas créer de
doublon ni perdre un événement, car chaque image est recalculée à partir du seul temps affiché.

## Modules

| Fichier | Responsabilité |
|---|---|
| `queuesmart/scene/layout.py` | `SceneLayout` : plan (entrée, sortie, allées, poste de service, places de file) et trajets par l'allée principale |
| `queuesmart/scene/queue_board.py` | `QueueBoard` : files FIFO reconstruites en rejouant les événements (les rangs sont recalculés, `queue_position` n'est pas utilisé hors arrivée) |
| `queuesmart/scene/tracks.py` | `CustomerTrack` : images clés (temps, position, état), interpolation, trajet interrompu sans saut |
| `queuesmart/scene/timeline.py` | `SceneTimelineBuilder` : un gestionnaire par type d'événement (dictionnaire, pas de `if/elif`) |
| `queuesmart/scene/html.py` | Assemble la page autonome (modules JS + données JSON) |
| `queuesmart/ui/scene_view.py` | Composant Streamlit (seul fichier de la scène qui importe Streamlit) |
| `frontend_2d/animations.js` | Échantillonnage des trajectoires (même règle que `tracks.py`) |
| `frontend_2d/event_player.js` | Horloge en minutes simulées, x1 à x5, pause, seek |
| `frontend_2d/map.js` | Décor : sol, portes, rayons, caisses, tapis, panneaux ouvert/fermé |
| `frontend_2d/characters.js` | Sprites pixel art dessinés en code, badges d'état |
| `frontend_2d/scene.js` | Canvas, mise à l'échelle, commandes, HUD, suivi d'un client |

## États des clients

| État | Déclencheur | À l'écran |
|---|---|---|
| `entrant` | `customer_arrived` / `queue_joined` | marche de l'entrée vers la dernière place de la file |
| `en_file` | arrivée à sa place | immobile, avance quand la file se libère |
| `en_service` | `service_started` | au poste de la caisse, badge €, le caissier scanne |
| `en_transfert` | `queue_switched` | badge ⇄, repasse par l'allée principale vers l'autre file |
| `abandon` | `customer_abandoned` | grisé, badge ✕, repart par l'entrée sans passer en caisse |
| `sortant` | `customer_departed` | marche vers la porte de sortie puis disparaît |

Une caisse fermée devient rouge (« FERMÉE ») ; si un client y est servi, le caissier reste
jusqu'à son départ. Les réaffectations viennent uniquement des `queue_switched` du moteur.

## Tests de réception (`tests/test_scene.py`, `tests/test_scene_page.py`)

| Test | Vérification |
|---|---|
| V01 | 1 caisse, 5 clients : ordre FIFO, tous sortent par la porte |
| V02 | 3 caisses, 30 clients, graine 42 : chaque client atteint la caisse choisie par le moteur ; rang recalculé = `queue_position` à l'arrivée |
| V03 | la file avance quand la tête est servie ; aucune superposition de clients en file ou en caisse, sur toute une simulation de 100 clients |
| V04 | changement de file : les deux files sont mises à jour |
| V05 | abandon : jamais en caisse, ressort par l'entrée, pas compté comme servi |
| V06 | fermeture d'une caisse occupée : le service n'est pas interrompu |
| V07 | 100 clients, 5 caisses : calcul < 1 s, données < 500 ko (fluidité vérifiée à l'écran à x5) |
| V08 | rejouer les mêmes événements donne exactement la même scène |
| V09 | vérifié à l'écran : la scène suit la largeur disponible (testé à 420 px et 1440 px) |
| V10 | l'affichage ne dépend que du temps (avant/arrière identiques) ; chaque événement appliqué une fois |

## Limites connues

- Les trajets sont visuels : un trajet dure au plus 0,9 × la durée minimale de service, pour
  qu'un client atteigne toujours la caisse avant la fin de son passage. Les attentes et KPI
  restent ceux du moteur.
- Au-delà de 20 clients dans une même file, les places se superposent (2 colonnes de 10).
- Les clients qui marchent dans l'allée principale peuvent se croiser (pas de collision entre
  piétons, seulement entre places de file).
- Ouverture/fermeture programmées avant la simulation, pas pilotables pendant la lecture.


## Intégration du 18 novembre 2026

La scène est disponible dans `app.py`, espace Simulation, puis Magasin.
`dynamic_demo.py` conserve un accès direct. La hauteur suit le contenu avec
`st.iframe`, et le canvas est plafonné à 480 px de haut pour éviter la zone de
1 100 px réservée par l’ancien composant.

Le lecteur propose x10 et x20, une avance au prochain événement, un choix du
client suivi, des raccourcis clavier et un tableau des caisses. Les compteurs
lisent les événements du moteur et se reconstruisent lors d’un retour en arrière.
Ils ne comptent pas les personnages encore visibles pendant leur trajet de sortie.
Les tests de logique se lancent avec `node tests/scene_controls.cjs`.
