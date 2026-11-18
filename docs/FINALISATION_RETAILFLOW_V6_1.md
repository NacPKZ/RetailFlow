# RetailFlow V6.1 : finalisation et validation

## Référence auditée

La Pull Request 2 pointe sur `b759b3a73a1d933edff26ed1dbb296cdcb1b3c20`.
Le travail V6.1 part de cette version dans une branche distincte, sans reconstruire le projet.
Les 231 tests existants passent. Ruff signale 97 diagnostics préexistants :
91 lignes trop longues, trois imports inutilisés, un import non trié, une convention
UTC et un appel à `zip` sans précision de longueur. Ces diagnostics ne sont pas assimilés
à des régressions de la V6.1.

## Audit préalable, avant modification

| Gravité | Constat vérifié dans les sources | Traitement prévu |
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

Cette partie sera complétée avec les corrections, les vérifications et les limites effectives.
