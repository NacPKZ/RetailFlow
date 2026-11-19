# Intégration de la mission 3 — Analytics et optimisation

## Environnement

Le projet demande Python 3.11 ou plus récent. Depuis la racine `RetailFlow/`, créer et activer un environnement virtuel Windows :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell bloque l'activation, utiliser directement `./.venv/Scripts/python.exe` devant les commandes ci-dessous. Dans VS Code, sélectionner l'interpréteur `.venv` via **Python: Select Interpreter**.

## Lancement

```powershell
python -m streamlit run app.py
```

Dans la navigation en haut, choisir **Analytics dynamique**. Cette page lance le moteur événementiel ; les pages historiques continuent à utiliser le moteur FIFO. Le fichier `dynamic_demo.py` reste une démonstration technique indépendante.

## Tests et vérifications

```powershell
python -m pytest -q
python -m compileall -q app.py queuesmart tests
python -m ruff check .
```

Pour exécuter uniquement les tests analytiques ajoutés :

```powershell
python -m pytest -q tests/test_dynamic_kpi.py tests/test_dynamic_comparison.py tests/test_dynamic_exports.py tests/test_dynamic_alerts.py
```

## Démonstration reproductible

1. Lancer `app.py` et ouvrir **Analytics dynamique**.
2. Garder une graine entière dans la configuration principale de la barre latérale ; le comparateur exige cette graine fixe.
3. Choisir le nombre initial de caisses, la patience et les options de changement de file.
4. Lancer la page et examiner les six zones : résumé, évolution, performance des caisses, distribution, comparaison et diagnostic.
5. Choisir un seuil d'attente. La recommandation est le plus petit nombre de caisses, entre 1 et 5, dont l'attente moyenne des clients servis est inférieure ou égale à ce seuil. Les abandons restent affichés séparément.
6. Exporter les tables CSV ou le classeur Excel. Les exports proviennent des mêmes objets de simulation et de rapport analytique que les graphiques.
7. Relancer avec les mêmes paramètres pour reproduire le scénario.

La comparaison est refusée lorsque la graine est absente ou lorsqu'un calendrier de changements de caisses est fourni : dans ce cas, un même calendrier d'identifiants de caisses ne garantit pas une capacité comparable de 1 à 5 caisses.

## Correspondance entre exigences, modules et tests

| Exigence du dossier | Implémentation principale | Test(s) |
|---|---|---|
| KPI servis, quantiles, services et abandon | `queuesmart/analytics/dynamic_kpi.py` | A01, A02, A04, A11 |
| Files et conservation des flux à t | `queuesmart/analytics/dynamic_kpi.py` | A05, A12 |
| Occupation et fermeture d'une caisse | `queuesmart/analytics/dynamic_kpi.py` | A03 et test de fin de service après fermeture |
| Indépendance de la vitesse de lecture | Rapport calculé indépendamment de l'animation | A06 |
| Dashboard dynamique | `queuesmart/ui/dynamic_dashboard.py`, intégré dans `app.py` | `tests/test_app.py` (à exécuter avec Streamlit installé) |
| Alertes sur seuils et périodes | `queuesmart/analytics/dynamic_alerts.py` | `tests/test_dynamic_alerts.py` |
| Comparaison contrôlée de 1 à 5 caisses | `queuesmart/analytics/dynamic_comparison.py` | tests de signature client identique et A10 |
| Recommandation au plus petit n conforme | `queuesmart/analytics/dynamic_optimizer.py` | A07, A08 |
| Exports CSV et Excel, y compris données vides | `queuesmart/exports/csv_export.py`, `excel_export.py` | A09, A01, A11 |
| Dictionnaire et conventions KPI | `docs/DICTIONNAIRE_KPI_DYNAMIQUES.md` | Revue documentaire |

## Limites connues et conventions

- Les simulations utilisent des clients synthétiques ; elles ne constituent pas une prévision du fonctionnement réel d'un magasin.
- L'attente moyenne et les quantiles portent uniquement sur les clients servis. Le temps passé avant abandon est un indicateur séparé.
- Les quantiles utilisent `statistics.quantiles(..., n=100, method="inclusive")` ; lorsqu'il n'y a qu'une observation, cette observation est retournée.
- Les états temporels sont reconstruits en rejouant les événements dans leur ordre initial. Un instant t est observé après tous les événements horodatés t.
- Une prestation commencée se termine après la fermeture de la caisse. Ce temps de terminaison est inclus dans la durée disponible effective du calcul d'occupation.
- Le moteur dynamique n'expose pas le sélecteur de stratégie FIFO. Il conserve sa règle propre d'affectation par attente estimée minimale.
- Une comparaison exige une graine fixe et refuse le calendrier de changements de caisses pour éviter une comparaison de capacité ambiguë.
- Si le seuil n'est atteint par aucune configuration, le résultat est `aucune configuration conforme` ; aucune valeur de remplacement n'est inventée.
- Le dépôt ne déclare pas de version applicative du moteur. Les exports consignent donc explicitement cette absence et la date de génération.
- Le rapport final calculé après simulation n'est pas un flux live. Les alertes résument les périodes observées et ne sont pas des notifications temps réel.
- Le test A11 utilise un résultat synthétique « tous abandonnés » : le moteur actuel commence le service d'un client lorsque la première caisse est disponible, ce qui empêche de créer naturellement ce scénario avec les options publiques actuelles sans modifier le moteur métier.
- Le test A06 vérifie l'indépendance du calcul analytique vis-à-vis d'une vitesse de lecture ; la vitesse x1/x5 de l'animation relève de la couche visuelle et ne pilote aucun calcul KPI.

## Livraison Git

Le travail est destiné à la branche `feature/dashboard-analytics` conformément au dossier de mission. Après avoir intégré ou copié ces fichiers dans le clone Git de l'équipe :

```powershell
git switch feature/dashboard-analytics
git pull origin main
python -m pytest -q
python -m streamlit run app.py
```

Vérifier le diff, puis créer une Pull Request vers `main` en joignant les résultats de tests, des captures du dashboard, les définitions KPI et un exemple d'export. Aucun commit ni aucune Pull Request n'a été créé dans le cadre de cette préparation.
