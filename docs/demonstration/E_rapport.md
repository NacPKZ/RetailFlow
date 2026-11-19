# RetailFlow | Démonstration V7 : rapport de décision

Projet universitaire de Master 2 BIDABI. Scénarios synthétiques.

## Hypothèses

Configuration : {'name': 'E_comparaison', 'customer_count': 110, 'arrival_window_min': 60, 'mean_service_time_min': 1.7, 'open_registers': 2, 'seed': 42}
Options dynamiques : {'patience_min': 12.0, 'switching_enabled': True, 'switching_interval_min': 1.0, 'switching_gain_min': 1.0, 'register_changes': (), 'customer_moves': (), 'manual_actions': ()}
Hypothèses économiques et service : {'hourly_cost': 22.0, 'abandonment_cost': 5.0, 'wait_target': 5.0, 'service_target': 90.0}

Graines testées : [42, 43, 44, 45, 46].

## Résultats simulés

| Caisses | Service moyen (%) | Minimum (%) | Abandons moyens | Coût moyen (€) | Admissible |
| --- | --- | --- | --- | --- | --- |
| 1 | 3.82 | 1.82 | 69.80 | 375.46 | False |
| 2 | 10.00 | 4.55 | 28.00 | 192.93 | False |
| 3 | 75.82 | 32.73 | 0.00 | 73.53 | False |
| 4 | 100.00 | 100.00 | 0.00 | 91.24 | True |
| 5 | 100.00 | 100.00 | 0.00 | 113.61 | True |

## Recommandation conditionnelle

4 caisses : coût moyen minimal parmi les capacités admissibles.

## Méthode et limites

Service : servis sous le seuil / tous les arrivants. Un abandon reste un échec.
Moyenne et P90 : clients servis seulement, puis moyenne des indicateurs par tirage.
Personnel : caisse-minutes mobilisées / 60 x coût horaire. Les caisses restent ouvertes jusqu'à la dernière sortie.
Abandons : nombre x coût hypothétique par abandon. Aucun chiffre d'affaires réel.
Les capacités partagent les mêmes graines, arrivées et services prévus. Les interventions de l'atelier sont exclues.
Les étendues min/max ne sont pas des intervalles de confiance. La conformité observée n'est pas une probabilité ni une garantie future.
Arrivées uniformes, services gamma, estimation d'attente avec information parfaite. Calibration terrain, pauses, compétences et coûts fixes non modélisés.
