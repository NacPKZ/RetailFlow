# RetailFlow | Index de la documentation

**Version de référence : V7, intégrée dans `main` le 19 novembre 2026.**

RetailFlow est un prototype universitaire de simulation et d'aide à la décision sur les files d'attente en supermarché. Les données, les coûts et les scénarios sont synthétiques. La documentation distingue la version actuelle de l'historique de développement.

## Guides actuels

| Document | Objet |
| --- | --- |
| [Présentation du projet](../README.md) | Problématique, application, installation, architecture et limites |
| [Version 7 et validation](VERSION_7_VALIDATION.md) | Fonctionnalités livrées, hypothèses, tests et réserves |
| [Architecture](ARCHITECTURE.md) | Modules, dépendances et conception |
| [Moteurs de simulation](MOTEURS_SIMULATION.md) | FIFO historique et simulation dynamique |
| [Scène 2D](SCENE_2D.md) | Rendu, interactions et limites |
| [Qualité du code](QUALITE_CODE.md) | Exemples de refactorisation et bonnes pratiques |
| [Crédits graphiques](CREDITS_GRAPHIQUES.md) | Origine des éléments graphiques |
| [Déploiement Streamlit](DEPLOIEMENT.md) | Source de l'application et contrôles navigateur |
| [Soutenance](SOUTENANCE.md) | Pitchs, démonstration et questions possibles |
| [Scénarios de démonstration](demonstration/scenarios.json) | Paramètres et scénarios reproductibles |
| [Rapport de décision simulé](demonstration/E_rapport.md) | Exemple de résultats et recommandations conditionnelles |

La présentation [PowerPoint](RetailFlow_Soutenance.pptx) est disponible séparément.

## Archives historiques

Ces documents retracent les étapes du projet et ne constituent pas les instructions d'exécution actuelles.

| Version | Document |
| --- | --- |
| V1 | [Contrat d'intégration](ARCHIVES_V1_CONTRAT_INTEGRATION.md) |
| V2 | [Transmission d'équipe](ARCHIVES_V2_TRANSMISSION.md) |
| V4 | [Évolution de l'interface](ARCHIVES_V4_INTERFACE.md) |
| V5 | [Refonte visuelle](ARCHIVES_V5_REFONTE_VISUELLE.md) |
| V6 | [Atelier interactif](ARCHIVES_V6_ATELIER_INTERACTIF.md) |
| V6.1 | [Finalisation et validation](ARCHIVES_V6_1_FINALISATION.md) |
| H1 à H7 | [Rapport technique de développement](ARCHIVES_RAPPORT_H1_H7.md) |

Les mesures de validation historiques sont conservées dans `validation_v6_1/` et les contrôles V7 dans `validation_v7/`.

## État GitHub et déploiement

- `main` contient la V7 et constitue la branche de référence pour le code et les documents.
- `feature/retailflow-v7-final` a été restaurée pour préserver la configuration existante de Streamlit Community Cloud.
- Les changements effectués sur `main` ne sont pas automatiquement visibles dans l'application tant que Streamlit déploie l'autre branche.
- Les vérifications de navigateur sont ciblées ; elles ne prouvent pas la compatibilité de tous les appareils ni la validation de bout en bout des exports PNG/JSON.

## Conventions

Les guides Markdown portent des noms explicites en majuscules avec underscores. Les archives commencent par `ARCHIVES_`. Les exports produits par les scripts conservent leurs noms de fichiers pour éviter de rompre la reproductibilité.

Pour démarrer : `python -m pip install -r requirements.txt` puis `python -m streamlit run app.py` depuis la racine du dépôt.
