# Déploiement Streamlit

Entrée officielle : `app.py`. Python 3.12, dépendances épinglées dans requirements.txt.
Les fichiers frontend_studio, frontend_2d et queuesmart doivent rester dans le dépôt.
Aucun secret ni base externe n'est nécessaire.

Configuration prête pour Community Cloud : dépôt NacPKZ/RetailFlow, branche
feature/retailflow-v7-final, fichier app.py. Ne pas sélectionner main tant que la
PR n'est pas fusionnée par l'équipe. La page Streamlit Community Cloud affiche une connexion requise dans le navigateur
de cette mission. Aucune session de compte authentifiée n'est disponible. Aucune URL publique
ne peut donc être annoncée comme déployée ou vérifiée.

Démarrage local : python -m streamlit run app.py.
Scénarios de secours : docs/demonstration. Reproduction : python scripts/livraison.py.
Validation : python -m pytest -q, puis npm run test:scene.
