# RetailFlow | Déploiement Streamlit

La V8 est en ligne depuis le 19 novembre 2026 sur [RetailFlow](https://retailflow-bidabi.streamlit.app/). La [PR #7](https://github.com/NacPKZ/RetailFlow/pull/7) a intégré le [commit de livraison `c73fc65`](https://github.com/NacPKZ/RetailFlow/commit/c73fc65a80f5a74379dc610eca42c6e65a23261f) dans `main`.

Streamlit utilise `app.py` sur la branche `feature/retailflow-v7-final`. Cette branche porte le commit de livraison V8. Pour une prochaine mise en ligne, avancer la branche Streamlit vers le commit validé dans `main`, puis vérifier la version affichée. Si Streamlit sert encore l’ancienne version, un redémarrage depuis le tableau de bord entraîne une brève interruption des sessions en cours.

## Contrôle de la V8 en production

Après le redémarrage, les journaux ont confirmé la récupération du code et le chargement des dépendances. Le navigateur a affiché **RetailFlow V8**, le pic d’affluence dans **Simulation**, le bilan dynamique dans **Analyses** et le bouton **Classeur Excel** dans **Journal et exports**. L’ouverture et la cohérence du classeur ont été contrôlées dans l’environnement local. Voir le [rapport de validation V8](VERSION_8_VALIDATION.md).

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

### Limites du contrôle V7

Contrôle ciblé sur ordinateur, sans audit exhaustif d'accessibilité ni appareil mobile.
La récupération automatisée de l'état JSON a expiré. Les exports PNG et JSON de scène
ne sont pas déclarés validés de bout en bout. Le contenu des archives est testé en Python.
Le ZIP téléchargé dans le navigateur n'a pas été réinspecté depuis le système de fichiers.
Aucune mesure de latence globale ni cadence garantie n'est revendiquée.

Démarrage local : python -m streamlit run app.py.
Scénarios de secours : docs/demonstration. Reproduction : python scripts/livraison.py.
Soutenance : docs/SOUTENANCE.md et docs/RetailFlow_Soutenance.pptx.
