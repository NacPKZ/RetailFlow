# RetailFlow | Arbitrages de l’intégration V8

Base `main` au commit `5e63b74`. La branche V7 `343e6dd` est son ancêtre, avec 40 commits d’écart. La branche analytics `133b4d5` porte un commit propre depuis l’ancienne interface. Son changement dans `app.py` introduisait une page autonome avec ses propres contrôles. L’intégration conserve l’interface et les moteurs de `main`.

| Fonctionnalité | V7 | Contribution analytics | Décision et motif |
| --- | --- | --- | --- |
| KPI et abandons | Bilan final, sorties et comparatif apparié | Durées détaillées par population | **Fusionner.** Tableau et exports partagent les KPI. Abandons et services terminés restent distincts. |
| Files et flux | Indicateurs de la scène et flux agrégés | États du journal par caisse | **Adapter.** Réutiliser `QueueBoard` et conserver l’ordre des événements simultanés. |
| Occupation | Mobilisation ouverte ou occupée | Intervalles effectifs | **Conserver** l’intégration V7. Ajouter les pics de file et services terminés par caisse. |
| Comparaison | Laboratoire et comparateur FIFO | Comparaison dynamique sur graines communes | **Fusionner** sur les tirages du laboratoire et conserver le comparateur FIFO historique. |
| Seuil d’attente | Coût et service | Capacité sous un seuil moyen | **Adapter.** Exiger la conformité de chaque tirage et afficher les abandons. |
| Alertes | Signalisation pendant la lecture | Seuils réglables sur le bilan | **Adapter.** Seuils explicites sur les mesures observées et intervalles de saturation. |
| Exports | CSV, JSON, PNG et ZIP | CSV KPI et classeur multi-onglets | **Fusionner.** Exports d’analyse alignés sur les mêmes tables. |
| Graphiques | Plotly et scène interactive | Files par caisse et distribution | **Fusionner** dans la page Analyses et le thème commun. |
| Point d’entrée et réglages | `app.py`, cinq espaces, atelier | Page et contrôles parallèles | **Écarter** les vues redondantes. Les paramètres et interventions viennent de l’atelier. |

La contribution d’origine reste consultable dans [le commit de la mission 3](https://github.com/NacPKZ/RetailFlow/commit/133b4d514e83f9c6758fa7a26a16425214808ead).
