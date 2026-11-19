# RetailFlow | Archives V6.1 : finalisation et validation

## Référence auditée

La Pull Request 2 pointe sur `b759b3a73a1d933edff26ed1dbb296cdcb1b3c20`.
Le travail V6.1 part de cette version dans une branche distincte, sans reconstruire le projet.
Les 231 tests existants passent. Ruff signale 97 diagnostics préexistants :
91 lignes trop longues, trois imports inutilisés, un import non trié, une convention
UTC et un appel à `zip` sans précision de longueur. Ces diagnostics ne sont pas assimilés
à des régressions de la V6.1.

## Audit préalable, avant modification

| Gravité | Constat vérifié dans les sources | Correction réalisée |
|---|---|---|
| Élevée | Le curseur serveur de la dernière intervention est réappliqué à chaque rerun, même après poursuite de la lecture | Consommer chaque demande de déplacement temporel une seule fois |
| Élevée | Le résultat renvoyé par le lecteur JavaScript contient des références mutables aux files d'un instant précédent | Renvoyer des instantanés indépendants et tester le retour temporel |
| Élevée | Les commandes manuelles sont rejouées avant certains événements déjà connus au même instant | Appliquer les commandes après les événements automatiques de l'instant, en gardant leur ordre |
| Élevée | Une intervention antérieure peut rendre une décision ultérieure inapplicable sans que l'historique le signale | Enregistrer les issues effectives du moteur, avec états avant et après |
| Élevée | Les files longues utilisent de nouvelles colonnes pouvant empiéter sur une autre caisse | Borner le dessin et signaler explicitement les groupes non dessinés |
| Moyenne | La comparaison dynamique ne présente pas moyenne, P90 et occupation | Ajouter des métriques et dénominateurs définis, sans mélanger les moteurs |
| Moyenne | L'inspecteur ne permet pas de recherche ni de chronologie complète | Enrichir l'inspecteur avec les seuls événements connus à l'instant choisi |
| Moyenne | Le déplacement de client dépend du glisser-déposer | Ajouter une alternative clavier et tactile par sélection |
| Moyenne | Le mode immersion peut nécessiter un défilement qui masque des commandes | Recomposer les zones flexibles et vérifier cinq tailles de viewport |
| Moyenne | Certaines fabriques de graphiques échouent sur un jeu vide | Définir un état vide commun et tester les données affichées |
| Moyenne | La pause au seuil peut être sautée à grande vitesse | Détecter le franchissement entre deux images |
| Facultative | Absence de parcours de soutenance guidé | Réutiliser les scénarios et commandes existants dans un guide discret |

Fonctionnalités confirmées par inspection et tests : deux moteurs, quatre espaces,
canvas, immersion, caméra, parcours de courses illustratifs, commandes validées par Python,
annulation, témoin, commentaires calculés, graphiques, répétitions et exports.
Le contrôle visuel n'est pas déduit du nombre de tests.

Limites déjà connues : données synthétiques, durées de service connues par le modèle,
cinq caisses dynamiques contre huit historiques, courses illustratives et validation
mobile non réalisée dans la version de référence.

## Mesures avant correction

Les fichiers `validation_v6_1/performance_avant.json` et `rejeu_avant.json`
conservent les mesures locales. Vingt configurations : 10, 60, 100 et 110 clients,
de une à cinq caisses. Médiane de trois exécutions pour le moteur. Ces temps dépendent
de l'environnement et ne constituent pas des garanties de performance.

## Résultat de la finalisation

### Architecture et périmètres

| Couche | Responsabilité conservée ou précisée |
|---|---|
| `app.py` | Interface principale unique, quatre espaces, accès aux deux moteurs |
| `simulation/engine.py` et stratégies | FIFO historique, comparaisons et recommandations |
| `simulation/dynamic.py` | Moteur événementiel, validation effective et issues des commandes |
| `analytics/interventions.py` | État à un instant donné, validation avant envoi et liste des interventions |
| `analytics/dynamic_metrics.py` | Bilans finaux appariés et intégration des ressources mobilisées |
| `scene/` | Traduction des événements en trajectoires et courses illustratives |
| `ui/studio_component.py` | Composant bidirectionnel, données Python et cache des trajectoires |
| `frontend_studio/replay.js` | Reconstruction indépendante des états connus à l'instant T |
| `frontend_studio/inspector.js` | Chronologie client et journal compact des décisions |
| `frontend_studio/painter.js` | Dessin du magasin et caméra, sans décision métier |
| `frontend_studio/studio.js` | Lecture, commandes, recherche, navigation et guide de soutenance |
| `ui/charts.py` | Graphiques partagés, unités, seuils et états vides |

Aucune interface parallèle ni nouvel optimiseur n'a été ajouté. Les moteurs, les
contributions antérieures et les outils historiques sont conservés.

### Fiabilité temporelle et interventions

Le curseur Python porte un jeton consommé une seule fois. Un changement d'analyse
ne ramène plus systématiquement la lecture à la dernière intervention.
Les instantanés JavaScript copient les files et états ; une lecture ultérieure ne
modifie plus un instantané déjà obtenu.

À un même instant, les commandes de l'atelier suivent les fins de service, changements
programmés, arrivées, échéances de patience et rééquilibrages déjà observés. Les commandes
simultanées conservent leur ordre de saisie. Les ordres programmés historiques gardent
leur priorité d'origine. Le moteur enregistre pour chaque commande son indice, son
instant, son application effective, son motif et les états avant et après.
Une modification dans le passé peut invalider une décision future : elle reste dans
le journal avec un motif explicite et ne produit aucun effet métier.

Les annulations retirent les commandes de la liste et recalculent la simulation.
Le scénario témoin garde les mêmes arrivants, durées prévues et options de base.
La conservation des clients est testée à des instants d'événements, y compris après
retours temporels et sur les vingt configurations demandées. Les options non finies
sont refusées pour éviter des relectures bloquées.

### Inspecteur et compréhension des actions

La recherche par identifiant complète le clic sur un sprite. L'inspecteur présente
statut, arrivée observée aux caisses, caisse actuelle, rang, changements de file,
attente cumulée, début de service, service écoulé et sortie ou abandon observé.
Sa chronologie ne lit que les événements antérieurs ou égaux à l'instant affiché.
Les événements futurs ne sont pas présentés comme des observations.

Le parcours dans les rayons est explicitement illustratif. Les compteurs distinguent
présence dans le dessin, courses illustratives, file, service et sorties du moteur.
Le client suivi porte un halo et son numéro. Une recherche permet aussi de suivre les
clients regroupés visuellement dans une file extrême.

Une sélection de caisse et un bouton Réaffecter offrent une alternative au glisser-déposer,
au clavier comme avec un dispositif de pointage. Les destinations fermées ou déjà choisies
sont désactivées. Les clients en service ne sont pas réaffectables.
Le journal est consultable à l'écran, sans dépendre d'une infobulle, et permet de revenir
à chaque décision. Les demandes impossibles sont expliquées par Python.

### Magasin, interface et animations

Le décor existant est préservé. Le tapis présente des produits pendant le scan et un
état de paiement en fin de service. Les proportions des personnages, le halo de suivi,
les couleurs de congestion et la hauteur des zones d'attente ont été ajustés.
Les courses illustratives utilisent davantage de positions de pause dans des allées libres.
Les tracés de suivi s'arrêtent aux points déjà parcourus.

Les files ne débordent plus sur les caisses voisines par création de colonnes infinies.
Au-delà de 18 personnes par caisse, les autres sont regroupées dans un badge indiquant
leur nombre. Elles restent toutes présentes dans le moteur et dans l'inspecteur.
La géométrie historique reste disponible pour l’export autonome de la scène V6.
Ce choix conserve une scène lisible ; il ne prétend pas simuler une occupation physique
réaliste pour une file arbitrairement longue.

Les textes secondaires et contrôles sont agrandis, les focus visibles conservés et les
boutons ont une cible minimale de 44 pixels avec leur bordure. Le panneau des caisses
suit la hauteur de la scène ; en immersion il ne déborde plus sur les outils.
Sous 900 pixels, il passe sous le magasin. La page utilise alors un défilement vertical
normal, plutôt que de masquer des commandes. Le bouton Suivre ne coupe plus son libellé.
La réduction des animations agit sur les mouvements décoratifs et transitions CSS.
Le franchissement d'une attente de cinq minutes est détecté entre deux images, même à x50.

### Graphiques et recommandations

Les graphiques existants sont conservés, sans doublon ajouté. Les titres de congestion
et d'attente par caisse sont formulés comme des questions de gestion. Les fabriques
acceptent des données filtrées vides, y compris la heatmap, qui échouait auparavant.
Les unités restent en minutes et clients ; les seuils sont à cinq minutes.
La caisse affichée dans le nuage et la heatmap dynamiques est la dernière affectation,
et l'attente couvre tout le parcours aux caisses. Cette limite est indiquée dans l'interface.

La comparaison finale montre moyenne et P90 des clients servis, clients servis,
abandons, niveau de service, occupation et ressources mobilisées. Le niveau de service
a pour dénominateur tous les arrivants. L'occupation est le temps de service divisé
par le temps où une caisse est ouverte ou termine un client, jusqu'à la dernière sortie
propre à chaque scénario. La mobilisation est exprimée en caisse-minutes.

Les résultats affichent l'effet combiné des décisions face au témoin. Ils n'isolent pas
l'effet de chaque commande et ne l'attribuent pas automatiquement à la dernière.
Un indicateur favorable ne suffit pas à conclure à un gain global.
Les CSV conservent leurs colonnes et le JSON d'expérience ajoute un schéma de version,
le bilan final et les issues effectives des décisions.

L'examen de `mean_wait_optimizer.py`, du recommandateur et de `compare_capacity`
confirme deux outils historiques distincts : moyenne sur un tirage, et cible combinant
P90 ≤ 5 min avec au moins 90 % des attentes ≤ 5 min sur plusieurs graines.
La page Comparaison explicite désormais moteur FIFO, comportement, paramètres et absence
d'abandons ou d'interventions dynamiques. Elle compare 1 à 8 caisses sur 5, 10 ou 20
répétitions identiques entre configurations. L'étendue des moyennes n'est pas un
intervalle de confiance. Une absence de configuration conforme est annoncée explicitement.
Aucune recommandation FIFO n'est présentée comme un optimum dynamique.

## Vérifications et résultats

| Contrôle | Résultat |
|---|---|
| Tests Python | 267 tests réussis, aucun échec ni test ignoré |
| Lecteur historique JavaScript | Réussi |
| Lecteur atelier JavaScript | Réussi, avec indépendance des états, inspecteur temporel et franchissement du seuil |
| Ruff sur tous les fichiers Python modifiés ou ajoutés | Aucun diagnostic |
| Ruff global | 97 diagnostics préexistants, mêmes familles de défauts ; commande non réussie globalement |
| `git diff --check` | Réussi |
| Scénario de secours | Deux productions identiques, commande appliquée et compromis vérifiés |
| Charge et annulations | 100 commandes, puis 50, 10, 1 et 0 conservée ; reproductibilité et conservation vérifiées |
| Contrat JavaScript/Python | États des files et caisses comparés sur un vrai payload, en avance et retour arrière |
| Formats CSV/JSON et graphiques vides | Sérialisation et affichage testés |

L'environnement signale un avertissement de dépréciation du greffon de tests anyio,
sans échec du projet. Les diagnostics Ruff anciens ne sont ni effacés ni présentés
comme une validation réussie du dépôt entier.

### Validation visuelle

Le navigateur a chargé l'application réelle dans une iframe dont le viewport CSS est
redimensionné par une page de contrôle locale. Les dimensions internes ont été lues
dans le DOM : il ne s'agit pas seulement d'images réduites. Les grandes tailles sont
ensuite mises à l'échelle pour tenir dans la capture. Les cinq formats ont été examinés
en immersion ; des contrôles complémentaires ont été réalisés dans la page normale.

| Viewport CSS | Contrôle observé |
|---|---|
| 1920 × 1080 | Magasin et panneau côte à côte, bornes du panneau égales à celles de la scène |
| 1366 × 768 | Commandes lisibles, panneau défilable, outils accessibles par défilement si nécessaire |
| 1024 × 768 | Contrôles sur deux lignes, panneau sans débordement horizontal |
| 768 × 1024 | Magasin large et panneau empilé sous la scène |
| 390 × 844 | Commandes réorganisées, recherche et réaffectation par sélection exécutées |

Aucun débordement horizontal n'a été mesuré : largeur défilante du document égale
à la largeur du viewport dans les cinq cas. Les valeurs sont conservées dans
[viewports.json](validation_v6_1/viewports.json).

Captures : [1920](validation_v6_1/captures/v61_1920.jpg),
[1366](validation_v6_1/captures/v61_1366.jpg),
[1024](validation_v6_1/captures/v61_1024.jpg),
[768](validation_v6_1/captures/v61_768.jpg),
[390](validation_v6_1/captures/v61_390.jpg) et
[soutenance avec intervention](validation_v6_1/captures/v61_soutenance.jpg).

Contrôles fonctionnels observés : ouverture d'une caisse validée par Python, transfert
par sélection avec changement de caisse et chronologie, déplacement au pic,
lecture accélérée jusqu'à la fin et accès à la comparaison recalculée.
Les lectures x1, x5, x20 et x50 ont été exercées sur le profil de 110 clients.
Les prélèvements locaux de temps de dessin figurent dans `mesures_canvas.json`.
Le navigateur de contrôle est limité ou ralenti entre les interactions : ces
prélèvements ne permettent pas d'annoncer une cadence stable en images par seconde.

Les boutons d'export sont présents et les formats côté Python sont contrôlés.
La récupération automatisée des fichiers téléchargés a expiré dans le navigateur
de contrôle. La validation binaire de bout en bout des téléchargements PNG, CSV et JSON
reste donc à effectuer dans un navigateur utilisateur. Elle n'est pas déclarée réussie.

L'émulation CSS ne valide ni Safari iOS, ni le geste tactile physique, ni le lecteur
d'écran. La solution par sélection est testée avec un dispositif de pointage dans
le viewport téléphone. Aucune conformité d'accessibilité exhaustive n'est revendiquée.

Pour reproduire le banc de contrôle local, copier `scripts/validation_viewports.html`
dans `static/validation.html`, puis démarrer Streamlit avec
`python -m streamlit run app.py --server.enableStaticServing true`.
Ouvrir ensuite `/app/static/validation.html` sur le même serveur. Ce fichier de contrôle
n'est pas une seconde interface produit et le service statique n'est pas activé par défaut.
Le bilan automatisé est conservé dans `validation_v6_1/tests.json`.

### Performance et choix de cache

Les vingt configurations de 10, 60, 100 et 110 clients avec 1 à 5 caisses ont été mesurées.
Les résultats bruts avant et après figurent dans `validation_v6_1/` et le script
`python scripts/benchmark_v61.py /tmp/retailflow_benchmark.json` permet de les reproduire.

Le moteur reste inférieur à 15 ms dans les mesures enregistrées. La préparation froide
du payload peut atteindre environ 183 ms après ajout du cache, contre 168 ms avant.
Ce coût n'est pas présenté comme une accélération générale. Les trajectoires sont
maintenant mises en cache dans huit entrées au maximum ; les changements de curseur et
de messages n'imposent plus leur reconstruction. Le passage à chaud observé est inférieur
à 22 ms dans cette mesure. Le cache moteur est également borné à 64 entrées.

Les 10 000 lectures JavaScript passent d'environ 79 à 131 ms : les copies supplémentaires
coûtent du temps mais empêchent la mutation d'états passés. Cela représente environ
0,013 ms par lecture dans ce microbenchmark, hors dessin. Les handlers documentaires et
observateurs sont toujours retirés lors du démontage. Le journal n'est plus reconstruit
à chaque image et le sélecteur de destination conserve son focus entre deux états identiques.

## Lancement et démonstration de trois à cinq minutes

Depuis la racine, avec l'environnement virtuel activé :

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Pour récupérer cette version après publication, sans fusionner :

```bash
git fetch origin
git switch feature/retailflow-v6-1
git pull --ff-only origin feature/retailflow-v6-1
python -m streamlit run app.py
```

Si la branche locale n'existe pas encore, `git switch --track origin/feature/retailflow-v6-1`
la crée à partir de la branche distante. Arrêter puis relancer Streamlit après le changement
de branche permet de recharger les assets du composant.

| Temps indicatif | Déroulé |
|---|---|
| 0:00 à 0:45 | Choisir Soutenance reproductible dans les réglages, conserver deux caisses, patience 12, abandons et rééquilibrage activés ; présenter les hypothèses |
| 0:45 à 1:30 | Activer Mode soutenance, étape Congestion ; observer le pic, les caisses et un client recherché par identifiant |
| 1:30 à 2:15 | Ouvrir la caisse 3 à l'instant du pic ; vérifier confirmation et journal. Une réaffectation peut illustrer une seconde décision, avec effet alors combiné |
| 2:15 à 3:30 | Quitter l'immersion si nécessaire, ouvrir l'analyse Interventions et comparer tous les indicateurs au témoin |
| 3:30 à 4:30 | Présenter gains partiels, capacité supplémentaire et limites statistiques ; conclure sur l'intérêt de tester plusieurs graines |

Le profil de soutenance dérive du scénario d'affluence existant : 110 clients sur
60 minutes, service moyen 1,7 min, graine 42. Avec deux caisses, le pic du témoin est
à 16,678416 min. Ouvrir uniquement la caisse 3 à ce pic fait passer, dans ce tirage,
les servis de 76 à 110 et les abandons de 34 à 0. L'attente moyenne des servis passe
de 9,53 à 8,40 min ; le P90 de 11,64 à 10,96 min. Le niveau de service sous cinq minutes
reste à 4,55 %, très loin de 90 %. Les ressources mobilisées augmentent de 55,32
caisse-minutes. Ce cas ne justifie donc pas d'annoncer que tous les objectifs sont atteints.

En cas de problème pendant l'oral, utiliser le résultat de secours fourni :
[JSON apparié](validation_v6_1/scenario_secours.json) et
[clients CSV](validation_v6_1/scenario_secours.csv).
Il se régénère avec `python scripts/prepare_soutenance.py`, sans lancer l'interface.
Les résultats restent une seule réalisation synthétique et ne sont pas des observations
réelles d'un supermarché.

## Limites restantes et revue

La scène illustre les trajectoires et les courses. Elle ne dispose pas d'un modèle de
collision physique entre piétons ; des croisements pendant les déplacements restent
possibles. Les regroupements des files extrêmes évitent leur débordement graphique,
sans ajouter une géométrie de file réelle au moteur.
Les paramètres sont synthétiques et l'attente estimée peut utiliser les durées de service
connues du modèle. Les comparaisons d'interventions portent sur une graine identique,
sans mesure isolée des effets individuels ni intervalle de confiance.

Les téléchargements binaires, les gestes sur appareil tactile réel et les autres moteurs
de navigateur restent des vérifications à réaliser. La dette de lint préexistante subsiste.
Aucun test n'a été supprimé et aucune fusion automatique n'a été réalisée.
La Pull Request V6.1 est destinée à la branche de la PR 2 pour ne présenter que ce complément ;
sa fusion dans main reste une décision de revue de l'équipe.
