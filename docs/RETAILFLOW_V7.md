# RetailFlow V7.0

Prototype universitaire d'aide à la décision, Master 2 BIDABI. Données synthétiques.
Le nom de l'édition décrit une ambition de présentation et de méthode ; aucun
usage commercial ni déploiement chez un distributeur n'est revendiqué.

## Base conservée

Les branches `feature/retailflow-v6-1` et `feature/retailflow-v7-final` pointaient
initialement vers `4ac03698f204d119a5d81fc540c971b1a3c4a948`.
La V7 prolonge cette base. Elle conserve les contributions, le moteur FIFO
historique, le moteur dynamique, les contrats et l'ancien lecteur autonome.
La PR V7 cible V6.1 pour présenter uniquement ce complément. La fusion des
branches précédentes et de cette PR reste une décision de l'équipe.

## Ce qui est livré

| Espace | Fonctions |
| --- | --- |
| Introduction | Explication en trois étapes : observer, tester, décider ; périmètres et limites |
| Centre de contrôle | Présentation navy et dorée, vue complète ou focus magasin, indicateur de lecture/pause/recalcul |
| Files | Une ligne verticale par caisse, six clients visibles au maximum, surplus exact affiché dans un badge |
| Animations | Marche interpolée, tapis, produits, scan et paiement illustratifs pendant le service ; désactivation des décorations |
| Caméra | Zoom 100 à 300 %, molette autour du pointeur, déplacements bornés, recentrage, cadrage des caisses |
| Mini-carte | Positions visibles et cadre de caméra ; clic pour se déplacer, activation/désactivation, touche Entrée pour recentrer |
| Inspection | Recherche par identifiant, rang réel, chronologie connue, suivi client avec caméra amortie |
| Caisses | Ouverture/fermeture validée par Python, attente actuelle, nombre de passages terminés, progression du service |
| Performance en direct | Attente moyenne et P90 des sortis servis, occupation cumulée des ressources, débit récent |
| Flux | Graphique synchronisé des files et services sur vingt minutes, résumé textuel accessible |
| Alertes | Clients au-delà de cinq minutes, occupation des caisses ouvertes, croissance mécanique de la file |
| Projection | Extrapolation à cinq minutes de la tendance observée sur les cinq dernières minutes |
| Lecture | Pause, reprise, pas suivant, x1 à x50, visite du pic, retour arrière, repères, plein écran |
| Exports de scène | Capture PNG existante et nouvel état JSON de l'instant affiché |
| Décision | Capacités fixes de 1 à 5 caisses, 5/10/20 graines, coûts hypothétiques, seuils de service, frontière coût/service |
| Sensibilité | Volume à 80 %, 100 %, 120 % à capacité identique ; recalcul et invalidation si changement de contexte |
| Dossier exportable | Rapport Markdown, paramètres JSON strict, synthèse et tirages CSV, graphique HTML autonome dans un ZIP |
| Qualité | Invariants FIFO, contrôle Python/JavaScript, cycle du composant, tests Streamlit, chaîne GitHub Actions |

Les fonctions déjà disponibles en V6.1 restent accessibles, notamment l'annulation,
la réaffectation par sélection, le journal des décisions et la comparaison au témoin.
La V7 n'ajoute pas de modèle de collision physique ni de gestion des pauses du personnel.

## Règles scientifiques

### Calcul et affichage

Le moteur produit les événements une seule fois par configuration. La vitesse,
le zoom, la caméra et les décorations n'entrent jamais dans ses paramètres.
Une intervention remonte au moteur Python puis déclenche un recalcul déterministe.
Les tests vérifient conservation, unicité et service de la tête de file après
chaque événement, y compris transferts et fermetures.

La condensation ne supprime personne : tous les identifiants, rangs et événements
restent disponibles. Au-delà du sixième rang, une ancre graphique virtuelle stable
évite des milliers de déplacements invisibles. Le vrai rang vient du journal.
Le lecteur historique conserve sa géométrie pour éviter une régression des exports.

Les phases de scan et de paiement sont des décorations du service en cours.
Elles ne constituent pas des événements de paiement ni des transactions observées.
Les courses en rayons restent illustratives et sont comptées séparément.
Les trajets n'intègrent pas d'évitement physique entre piétons.

### Indicateurs à l'instant affiché

Le module `frontend_studio/operations.js` indexe le journal et ne retourne que son
préfixe connu. Un retour arrière ne révèle ni départ ni abandon futur.

- Attente moyenne et P90 : clients déjà sortis après service, attente entre arrivée
  et début de service. P90 interpolé. Sans sortie, affichage « Indisponible ».
- Occupation : service cumulé / mobilisation cumulée. Une caisse fermée qui termine
  un client reste mobilisée. Le calcul s'arrête à la dernière sortie métier,
  indépendamment de la fin de l'animation.
- Débit : sorties servies sur les cinq dernières minutes, ramenées à une heure.
  Au début, la fenêtre est plus courte. Ce n'est pas une capacité garantie.
- Évolution du flux : nombres instantanés de clients en file et en service.
- La mesure « ms / dessin » porte seulement sur le dessin principal, pas sur le
  rendu global, le DOM, les graphiques, la latence Python ou une cadence garantie.

### Projection, hypothèse explicite

À partir de cinq minutes d'observation :

`file à +5 min = max(0, file actuelle + arrivées récentes - débuts de service récents - abandons récents)`

La fenêtre récente dure cinq minutes. Les changements de file ne modifient pas
l'effectif total en attente. La projection suppose les rythmes constants et ne
lit pas les futurs événements du scénario. Ce n'est ni un modèle statistique de
prévision, ni une estimation calibrée sur des données de magasin. Une ouverture
de caisse ou une rupture d'affluence peut invalider immédiatement cette tendance.

### Laboratoire dynamique

Les capacités utilisent exactement les mêmes arrivants et services prévus pour
chaque graine. La patience et le rééquilibrage sont ceux de l'atelier. Les actions
manuelles et les ouvertures programmées sont exclues : les capacités restent fixes.
Le module de calcul refuse des options d'intervention et les comparaisons sans
graine explicite, plutôt que de produire un appariement trompeur.

- Niveau de service : clients servis sous le seuil / tous les arrivants. Un abandon
  reste un échec. Le seuil et la cible sont modifiables.
- Coût personnel : caisse-minutes effectivement mobilisées / 60 x coût horaire.
  Toutes les caisses fixes restent ouvertes jusqu'à la dernière sortie.
- Coût d'abandon : nombre d'abandons x coût unitaire hypothétique saisi.
- Coût modélisé : personnel + abandons. Aucun revenu, panier réel, marge, coût fixe,
  pause ou productivité individuelle n'est estimé.
- Synthèse : moyenne des indicateurs par tirage. Le P90 affiché est la moyenne des
  P90 des servis, pas le percentile de clients regroupés de toutes les graines.
- Admissibilité : cible respectée dans chacun des tirages testés.
- Recommandation : coût moyen minimal parmi les capacités admissibles. En cas
  d'égalité, moins de caisses. Si aucune ne convient, aucune recommandation.
- Frontière de Pareto : aucune capacité n'offre un service moyen au moins égal à
  coût moyen inférieur ou égal, avec au moins une amélioration stricte.

Les étendues min/max ne sont pas des intervalles de confiance. La conformité des
répétitions n'est pas une probabilité de réussite ni une garantie terrain.
L'hypothèse d'information parfaite sur la durée simulée des services est conservée.
La sensibilité change le nombre de clients ; entre volumes, les arrivants générés
peuvent changer. L'appariement strict concerne les capacités d'un même volume.

## Architecture ajoutée

| Module | Responsabilité |
| --- | --- |
| `queuesmart/analytics/decision_lab.py` | Hypothèses validées, simulation appariée, calcul économique, sélection, rapport et archive |
| `queuesmart/ui/decision_lab.py` | Formulaire, cache borné, invalidation, graphique, restitution et téléchargements |
| `frontend_studio/operations.js` | Index des événements, statistiques de préfixe et graphique synchronisé |
| `frontend_studio/painter.js` | Géométrie de caméra, rendu, condensation et mini-carte |
| `frontend_studio/studio.js` | Cycle du composant, commandes et préférences locales |
| `scripts/benchmark_v7.py` | Charge Python à 100 et 500 clients, sans mesure de navigateur |
| `.github/workflows/quality.yml` | Tests Python et JavaScript, lint ciblé, contrôle du diff |

Le nouveau JavaScript a été mis en forme pour faciliter sa lecture et sa maintenance.
Les caches existants restent bornés ; le laboratoire conserve au plus seize calculs
et une seule synthèse courante par session. Les exports sont générés à la demande
du résultat du formulaire. Changer les paramètres exige un nouveau calcul.

## Démonstration en cinq minutes

1. Ouvrir `python -m streamlit run app.py`, puis l'introduction en trois étapes.
2. Choisir « Soutenance reproductible » dans les réglages, conserver patience 12 min,
   abandons et rééquilibrage, puis cliquer « Voir le pic ».
3. Montrer la ligne unique et le badge de surplus, inspecter un client, utiliser
   la mini-carte et afficher le graphique synchronisé. Distinguer courses et caisses.
4. Ouvrir une caisse fermée. Attendre le retour Python et consulter « Interventions »
   pour comparer le bilan final au témoin sur la même clientèle.
5. Choisir « Laboratoire de décision », expliciter les hypothèses de coût, lancer
   l'évaluation sur cinq graines et commenter admissibilité, coût et Pareto.
6. Télécharger le dossier ZIP. Conclure sur les limites : synthétique, non calibré,
   une projection mécanique et des coûts hypothétiques.

Le mode soutenance V6.1 et son résultat de secours restent disponibles. Pour
préparer une démonstration hors connexion, exporter le ZIP après une évaluation ;
son graphique HTML embarque Plotly et fonctionne sans CDN.

## Validation et limites de cette livraison

286 tests Python réussis, sans échec ni test ignoré. Trois suites JavaScript
réussies, Ruff ciblé et `git diff --check` réussis.
Les résultats de tests et les mesures sont consignés dans `validation_v7/`.
Les tests couvrent notamment :

- conservation et FIFO événement par événement, transferts et abandons ;
- identité des arrivées/services entre capacités d'une même graine ;
- formules de coûts, dénominateurs, sélection sans arrondi, absence de solution ;
- concordance des statistiques JavaScript finales avec les calculs Python ;
- absence de lecture du futur, retours arrière et caméra bornée ;
- montage du composant avec un vrai payload, lecture x50, suivi, préférences,
  commande envoyée à Python et nettoyage des écouteurs ;
- parcours Streamlit, évaluation, sensibilité, invalidation des résultats ;
- contenu et intégrité du ZIP, BOM UTF-8 des CSV, paramètres reproductibles ;
- préservation de tous les clients et du journal dans une scène dense.

Le test du montage utilise un DOM simulé et un contexte de dessin factice.
Il détecte des erreurs de cycle et de commandes, mais ne prouve pas la qualité
visuelle. L'aperçu local n'a pas été accessible depuis le navigateur de contrôle.
La validation visuelle de V6.1 n'est pas présentée comme une validation de V7.

Restent à vérifier sur l'application réelle : ordinateur et téléphone, recadrage,
plein écran, interaction tactile, débordements, contraste du canvas, lecteur
d'écran, captures PNG et téléchargements de bout en bout. Aucun objectif de
60 images/s ni absence de chevauchement des trajets en mouvement n'est garanti.
La carte est accessible par commandes alternatives, mais le canvas ne représente
pas à lui seul une interface complète pour lecteur d'écran.

Ces limites motivent une PR en brouillon jusqu'à la revue visuelle de l'équipe.

## Consolidation finale

Accueil et méthodologie intégrés. Interventions isolées dans un fragment Streamlit.
Exports lourds mis en cache. Médiane et P95 ajoutés aux résultats dynamiques.
Cinq scénarios calculés dans demonstration/, scripts et contenu oral dans SOUTENANCE.md.
Le déploiement public nécessite une connexion au compte Streamlit, page de connexion observée.
