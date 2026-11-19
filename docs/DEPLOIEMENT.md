# RetailFlow | Déploiement Streamlit

Application : https://retailflow-nacpkz.streamlit.app/

Déployée et démarrée le 19 novembre 2026 sur Streamlit Community Cloud.
Dépôt NacPKZ/RetailFlow, branche feature/retailflow-v7-final, entrée officielle app.py.
Python 3.12.16 observé dans les journaux. Aucun secret applicatif requis.
La version V7 a été intégrée dans `main` le 19 novembre 2026. La branche `feature/retailflow-v7-final` a été restaurée et reste la source configurée pour le déploiement Streamlit. Les mises à jour de `main` ne sont pas automatiquement déployées tant que la configuration Streamlit pointe vers cette branche.

## Validation V8

Le candidat V8 est préparé sur `integration/retailflow-v8-analytics`. Voir [la validation V8](VERSION_8_VALIDATION.md) pour les contrôles locaux. Après validation GitHub, vérifier la branche configurée dans Streamlit Community Cloud. Si la configuration pointe toujours vers `feature/retailflow-v7-final`, publier le commit validé sur cette branche par avance rapide. Conserver `app.py` et l’URL existante. Contrôler ensuite le titre V8, le chargement de la scène et le téléchargement Excel depuis cette URL.

## Contrôle historique V7 en navigateur

Accueil chargé. Navigation Simulation, Analyses, Optimisation et Méthodologie vérifiée.
Lecture et pause observées avec avancement du temps, zoom à 120 %, recentrage à 100 %,
plein écran, ouverture de la caisse 4 et réaffectation du client 15 depuis la caisse 1
vers la caisse 4 confirmées par le journal Python. Instant 13:58 et zoom conservés
après les interventions. Le client passe en service sur la caisse 4.

Laboratoire exécuté sur 50 clients, cinq graines, coût horaire 22 €, coût d'abandon
hypothétique 5 €, cible 90 % servis sous cinq minutes. Recommandation observée : trois
caisses. Le téléchargement du dossier ZIP retourne un chemin de téléchargement terminé.

Capture réelle : validation_v7/retailflow_public.jpg.

## Limites du contrôle

Contrôle ciblé sur ordinateur, sans audit exhaustif d'accessibilité ni appareil mobile.
La récupération automatisée de l'état JSON a expiré. Les exports PNG et JSON de scène
ne sont pas déclarés validés de bout en bout. Le contenu des archives est testé en Python.
Le ZIP téléchargé dans le navigateur n'a pas été réinspecté depuis le système de fichiers.
Aucune mesure de latence globale ni cadence garantie n'est revendiquée.

Démarrage local : python -m streamlit run app.py.
Scénarios de secours : docs/demonstration. Reproduction : python scripts/livraison.py.
Soutenance : docs/SOUTENANCE.md et docs/RetailFlow_Soutenance.pptx.
