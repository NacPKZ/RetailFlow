# RetailFlow | Validation de la V8

Les cinq espaces de `app.py` donnent accès à une scène interactive, un bilan dynamique du scénario joué, l’analyse FIFO historique, deux objectifs d’optimisation et leur méthodologie. La [matrice d’intégration](INTEGRATION_MISSION_3.md) documente les choix par fonctionnalité. Le [dictionnaire](DICTIONNAIRE_KPI_DYNAMIQUES.md) précise les calculs, populations, seuils, fenêtres et exports.

## Validation avant la mise en ligne

| Contrôle | Résultat |
| --- | --- |
| Pytest sous Python 3.12 | 301 tests réussis. Un avertissement de dépréciation dans le plugin pytest d’AnyIO de l’environnement |
| GitHub Actions | Workflow Qualité RetailFlow validé pour la [PR #7](https://github.com/NacPKZ/RetailFlow/pull/7/checks) |
| Compilation Python | `python -m compileall -q app.py queuesmart tests` réussi |
| JavaScript | Les trois scripts de `npm run test:scene` réussis |
| Ruff ciblé | Fichiers Python modifiés et périmètre historique du workflow valides |
| Ruff global | 96 diagnostics historiques, identiques à la base précédant la V8 |
| Dépendances | `python -m pip check` réussi |
| Navigateurs | Chromium local à 1 440 px et mobile émulé à 390 px, avec préférence de mouvement réduit |

Les tests vérifient des valeurs de quantiles avec une fixture indépendante, les événements simultanés, la conservation des clients, les fenêtres partielles, les cas sans service terminé, les durées avant abandon, le débit, l’occupation et les trajectoires pour une à cinq caisses. Ils rouvrent aussi le classeur et comparent les valeurs exportées.

Dans Chromium sur ordinateur, les cinq pages, la pause, le pic, le zoom, le recentrage, le plein écran, l’ouverture et la fermeture d’une caisse, l’inspection d’un client, sa réaffectation et le maintien de l’instant après une intervention ont été vérifiés. Les deux objectifs d’optimisation ont été lancés. Les téléchargements PNG et JSON de scène, CSV, XLSX, JSON de bilan et ZIP de décision ont été récupérés et ouverts. À 390 px, les analyses et la scène restent dans la largeur disponible et les animations décoratives sont désactivées par la préférence système.

## Captures réelles

- [Scène 2D sur ordinateur](validation_v8/scene-desktop.jpg)
- [Analyses sur ordinateur](validation_v8/analyses-desktop.jpg)
- [Analyses sur mobile émulé](validation_v8/analyses-mobile.jpg)

## Contrôle en production

Le 19 novembre 2026, après redémarrage de [RetailFlow sur Streamlit](https://retailflow-bidabi.streamlit.app/), le navigateur a confirmé la V8, l’accès au pic de la simulation, le chargement du bilan dynamique et la présence de l’action **Classeur Excel**. Le [guide de déploiement](DEPLOIEMENT.md) indique la branche de production et le commit livré.

## Limites

Le parcours navigateur est ciblé. Les contrôles couvrent Chromium sur ordinateur et un mobile émulé en local. La cadence de rendu, l’accessibilité complète et les appareils mobiles physiques restent à évaluer.
