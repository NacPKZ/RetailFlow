# RetailFlow | Indicateurs dynamiques

Le bilan **Analyses** couvre le scénario de l’atelier et ses interventions validées. Les minutes sont comptées depuis l’ouverture. La fenêtre se termine au dernier service terminé ou abandon. Un journal partiel s’arrête au dernier événement fourni. Les courses dessinées sont illustratives. Le lecteur exploite le journal jusqu’à l’instant choisi.

| Indicateur | Population et calcul |
| --- | --- |
| Arrivés, servis, abandons, présents | Arrivés = servis sortis + abandons + clients en file ou en service |
| Attente moyenne, médiane, P90, P95, maximum | Début du service − arrivée aux caisses, pour les services terminés. Les percentiles utilisent une interpolation linéaire |
| Service moyen | Moyenne des durées de service des clients servis et sortis |
| Temps dans le système | Sortie − arrivée aux caisses, pour les clients servis et sortis |
| Temps avant abandon | Instant d’abandon − arrivée aux caisses, pour les clients abandonnés |
| Taux d’abandon | Abandons / arrivés × 100 |
| Niveau de service | Servis avec une attente inférieure ou égale au seuil / arrivés × 100. Seuil de 5 min pour le bilan, ajustable dans le laboratoire |
| Débit du bilan | Services terminés / minutes depuis l’ouverture. Le débit du lecteur porte sur les cinq dernières minutes observées |
| En file, en service, présents | État après tous les événements de même minute, dans l’ordre du moteur. Présents = en file + en service |
| Pic de file par caisse | Plus grand nombre de personnes en attente après un lot d’événements de même minute |
| Durée mobilisée par caisse | Minutes pendant lesquelles la caisse est ouverte ou termine un service déjà commencé |
| Occupation | Minutes en service / minutes mobilisées. Le taux global utilise les sommes sur toutes les caisses |

Les moyennes sur une population vide sont indisponibles. Le bilan affiche zéro pour les taux rapportés aux arrivants lorsque la population est vide. Une caisse jamais mobilisée a une occupation indisponible.

## Alertes

La saturation signale un intervalle de durée positive pendant lequel l’effectif en file atteint le seuil choisi. Les autres règles utilisent le P90, le taux d’abandon, l’occupation faible et l’écart maximal entre caisses mobilisées. Les valeurs par défaut servent à explorer un scénario. L’estimation d’attente du moteur utilise les durées de service simulées connues d’avance et se distingue de l’attente enregistrée dans le bilan.

## Comparaison de capacités

De 1 à 5 caisses, avec 5, 10 ou 20 graines. Pour chaque graine, toutes les capacités utilisent la même clientèle et les mêmes services prévus. Les interventions sont exclues de l’optimisation. La comparaison **Interventions** utilise la même graine et la même clientèle avant et après les actions.

- **Niveau de service et coût.** Retenir le coût moyen minimal parmi les capacités qui atteignent la cible à chaque tirage. Un coût identique favorise le plus petit nombre de caisses. Coût du personnel = caisse-minutes / 60 × coût horaire. Coût des abandons = nombre × coût unitaire.
- **Seuil d’attente moyenne.** Retenir la plus petite capacité dont la moyenne des clients servis est inférieure ou égale au seuil à chaque tirage. Un tirage sans service est non conforme. Le taux d’abandon est affiché séparément. Une faible attente parmi les servis peut coexister avec de nombreux abandons.

Les configurations et graines choisies bornent l’interprétation. Les coûts sont hypothétiques. Les étendues observées ne sont pas des intervalles de confiance. Un usage opérationnel demanderait une calibration terrain.

## Contrats des exports

| Export | Contenu |
| --- | --- |
| CSV clients, KPI, événements et files | Tables du scénario complet, UTF-8 avec BOM, séparateur point-virgule, décimales à virgule |
| XLSX | Paramètres, Résumé KPI, Caisses, Clients, Événements et Files. Valeurs numériques dans des cellules numériques |
| JSON de l’expérience | Configuration, options, actions, résultat des interventions et KPI finaux. Schéma `retailflow-experience/7.0` enrichi de façon additive |
| JSON et PNG de la scène | État ou image à la minute affichée |
| Exports d’optimisation | Dossier ZIP avec coûts et hypothèses, rapport Markdown, ou CSV de comparaison d’attente |

Dans la table des clients, la colonne Service porte la durée générée pour le client. Cette durée est réalisée pour les services terminés.
