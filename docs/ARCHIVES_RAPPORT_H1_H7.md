# RetailFlow | Archives : rapport technique H1 à H7

**Date :** 17 novembre 2026  
**Statut historique au 17 novembre 2026 (avant intégration V7) :** base technique transmise, tests automatisés de l'application mis à jour et exécutés localement le 17 novembre 2026 ; intégration 2D et analytics finale encore en attente.  
**Nature des heures :** H1 à H7 sont sept créneaux de travail planifiés, pas un relevé chronométré des heures effectivement passées.

## 1. Objectif et périmètre

Réutiliser le projet QueueSmart initial développé par le premier membre, le fiabiliser, ajouter un moteur événementiel compatible avec une future scène 2D et préparer l'analyse. Le projet est un **simulateur pédagogique de files d'attente**, pas un jeu vidéo. La visualisation pixel art et le dashboard définitif seront réalisés par les membres 2 et 3.

## 2. H1 : audit du projet existant

- Code initial organisé en `queuesmart/domain`, `simulation`, `analytics` et `ui`.
- Application Streamlit historique dans `app.py`.
- Tests préexistants et documentation conservés.
- Points de divergence avec le cahier des charges : ancienne interface abstraite, jusqu'à huit caisses dans certains calculs historiques, optimiseur historique basé sur le p90 et un taux de dépassement plutôt que sur la seule attente moyenne, absence de gestion dynamique complète dans le moteur initial.
- **Précision :** le moteur historique n'a pas été supprimé ni entièrement réécrit.

## 3. H2 : contrat d'événements et optimisation

- Ajout de `queuesmart/simulation/events.py`, convertisseur d'une simulation historique en événements.
- Ajout de `queuesmart/analytics/mean_wait_optimizer.py`, optimiseur expérimental selon le seuil d'attente moyenne.
- Tests spécifiques dans `tests/test_events_contract.py` et `tests/test_mean_wait_optimizer.py`.
- Les événements dérivés de l'ancien moteur ne remplacent pas le moteur dynamique.

## 4. H3 et H4 : moteur événementiel dynamique

- Ajout de `queuesmart/simulation/dynamic.py` et de ses tests dans `tests/test_dynamic.py`.
- Prise en charge de 1 à 5 caisses, arrivées, files FIFO, choix selon l'attente estimée, changements de file, abandon sur patience, ouvertures et fermetures programmées.
- Graine aléatoire configurable pour reproduire un scénario.
- Fermeture : terminer le service en cours et réaffecter les clients en attente. La dernière caisse active ne peut pas être fermée.
- **Limite :** l'ouverture/fermeture en direct par un contrôle graphique n'est pas encore intégrée. Les changements sont programmés dans la configuration avant exécution.

## 5. H5 : interface pour le membre 2D

- Les événements `DynamicEvent` comportent `time`, `type`, `customer_id`, `register_id`, `target_register_id` et `queue_position`.
- Le membre 2 doit animer ces événements sans inventer de décisions métier.
- La future scène doit représenter l'entrée, les files, les caissiers, les changements de file, les départs et les abandons.
- Référence de transmission : `docs/ARCHIVES_V2_TRANSMISSION.md` et `docs/ARCHIVES_V1_CONTRAT_INTEGRATION.md`.

## 6. H6 : interface pour le membre analytics

- `DynamicResult` expose les clients, les événements, les nombres servis et abandonnés et l'attente moyenne des clients servis.
- Le dashboard final devra calculer et documenter ses dénominateurs, distinguer clients servis et abandonnés, comparer les configurations et exporter les résultats.
- L'ancien optimiseur p90 est toujours présent dans l'application historique. Il ne doit pas être présenté comme le nouvel optimiseur d'attente moyenne.

## 7. H7 : tests, interface et conditionnement

### Vérifications réalisées précédemment

- **162 tests réussis** lors de l'exécution `python -m pytest -q --ignore=tests/test_app.py`, selon le journal conservé dans `docs/RESULTATS_TESTS_H1_H7.txt`.
- Des scénarios de simulation complémentaires ont été exécutés lors de la séance précédente. Leurs résultats ne remplacent pas un test navigateur ni une validation d'intégration.
- La couverture précédemment mesurée était d'environ 70 % au global et 91 % pour le moteur dynamique. Ces valeurs ne sont pas recalculées par le présent rapport.

### Améliorations visuelles de cette livraison

- Création de `queuesmart/ui/theme.py`, thème commun Streamlit bleu marine, blanc et doré.
- `app.py` : nouvel en-tête et identification claire de la version historique.
- `dynamic_demo.py` : nouvel en-tête, cartes KPI et deux graphiques Plotly pour les événements et la distribution des attentes.
- Le style ne change pas les calculs métier.

### Vérifications restantes

- Exécuter **toute** la suite de tests sur le PC Windows avec les dépendances installées, notamment `tests/test_app.py`.
- Vérifier visuellement les deux applications dans le navigateur, sur écran large et mobile.
- Intégrer la scène pixel art du membre 2 et le dashboard du membre 3.
- Tester les contrôles en direct et l'intégration de bout en bout avant publication de la version finale.

## 8. Transmission et organisation

| Responsable | Périmètre | Échéance prévue |
|---|---|---|
| Membre 1 | Base initiale réalisée | Déjà fournie |
| Responsable intégration | Audit, tests, contrats, habillage commun, réception, documentation, PowerPoint et oral | Mardi, samedi, dimanche, lundi |
| Membre 2 | Supermarché 2D pixel art, sprites, files et animations synchronisées | Mercredi et jeudi, remise vendredi |
| Membre 3 | Dashboard final, KPI, comparaison, recommandation et exports | Mercredi et jeudi, remise vendredi |

**Vendredi :** réception des contributions. **Samedi :** intégration et tests Streamlit. **Dimanche :** documentation, PowerPoint et préparation orale. **Lundi :** répétition générale.

## 9. Commandes Windows

Dans le dossier contenant `app.py` et `requirements.txt` :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Pour le banc d'essai dynamique, arrêter le premier serveur puis exécuter :

```powershell
.\.venv\Scripts\python.exe -m streamlit run dynamic_demo.py
```

## 10. Publication GitHub et collaboration

Cette archive est une **base de travail commune**, pas la version finale après intégration des camarades. Publier le code sans `.venv`, caches, fichiers `.coverage` ni données sensibles. Vérifier les tests, les licences des futurs sprites et la cohérence du README avant la mise en ligne publique.


## 11. Mise à jour après H7 (17 novembre 2026)

- Le projet public porte désormais le nom **RetailFlow** ; le package technique conserve `queuesmart`.
- L'interface principale `app.py` a été remaniée autour de quatre vues : Vue d'ensemble, Simulation, Analyse et Comparaison.
- Les tests `tests/test_app.py` ont été adaptés à cette navigation. L'exécution locale `python -m pytest -q` communiquée le 17 novembre affiche 100 % de tests réussis, sans échec ; ce résultat ne vaut pas validation visuelle dans un navigateur.
- Le dépôt GitHub et les branches `feature/simulation-2d` et `feature/dashboard-analytics` ont été créés.
- La synchronisation du moteur dynamique avec la scène 2D et le dashboard final reste à effectuer.

Les chiffres de couverture et de tests indiqués dans les sections précédentes sont des **mesures historiques**, non recalculées dans cette mise à jour.
