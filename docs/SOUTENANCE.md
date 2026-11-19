# Soutenance RetailFlow

## Pitch de trente secondes

RetailFlow est un prototype universitaire qui simule les files d'attente d'un supermarché. Nous cherchons à limiter l'attente sans ouvrir inutilement trop de caisses. Le moteur calcule les arrivées, les services, les abandons et les changements de file. La scène permet de tester une ouverture de caisse et d'en mesurer l'effet. Le laboratoire compare ensuite les capacités sur les mêmes graines, avec des coûts hypothétiques. Les résultats sont reproductibles, mais demanderaient une calibration avant tout usage terrain.

## Pitch de deux minutes

Notre question est simple : combien de caisses mobiliser pour offrir un service satisfaisant ? Ouvrir davantage de caisses réduit souvent l'attente, mais mobilise plus de ressources. Nous avons donc construit RetailFlow pour explorer ce compromis.

Le projet combine Python, Streamlit et un lecteur graphique JavaScript. Le moteur événementiel applique FIFO dans chaque caisse. Il génère les arrivées et les services, puis traite les abandons selon la patience et les réaffectations. La scène rejoue ce journal. Accélérer la lecture ne change pas les résultats.

Nous pouvons ouvrir ou fermer une caisse, déplacer un client encore en file et comparer le bilan au scénario témoin. Les mêmes arrivées et services sont conservés. Le laboratoire compare plusieurs capacités sur plusieurs graines, avec des objectifs de service et des hypothèses de coût explicites.

Nous suivons notamment l'attente moyenne, les percentiles, les abandons et la mobilisation des caisses. Un abandon reste un échec dans le niveau de service, même si son attente était courte. Les coûts n'utilisent aucune donnée financière réelle.

La principale limite est que les données sont synthétiques. Les parcours en rayons sont illustratifs et l'estimation des files dispose d'une information parfaite sur les services simulés. L'intérêt du projet est de fournir une expérimentation reproductible et de montrer comment justifier une décision avec ses hypothèses.

## Contenu PowerPoint, douze diapositives, dix à quinze minutes

| Diapositive | Message à afficher | Commentaire oral |
| --- | --- | --- |
| 1. RetailFlow | Simulation et optimisation des files d'attente. Master 2 BIDABI | Présenter la question et l'équipe, sans attribution individuelle inventée. |
| 2. Problématique | Attente des clients et mobilisation des caisses | Expliquer le compromis coût et qualité. |
| 3. Objectifs | Observer les files et comparer des décisions reproductibles | Introduire les KPI et les contraintes. |
| 4. Architecture | Python calcule les événements. JavaScript les rejoue. Streamlit pilote les paramètres | Distinguer le moteur et l'affichage. |
| 5. Méthode | Arrivées uniformes, services gamma, FIFO par caisse | Expliciter les hypothèses et la graine 42. |
| 6. Comportements | Patience, abandon, rééquilibrage et fermeture progressive | Une fermeture termine le client en service. |
| 7. Simulation | Une ligne par caisse, six clients visibles, surplus exact | Passer à la démonstration. |
| 8. Interventions | Même clientèle avant et après décision | Ne pas confondre effet combiné et effet individuel. |
| 9. Indicateurs | Attente moyenne, médiane, P90, P95 et niveau de service | Dénominateurs : servis pour les attentes, tous les arrivants pour le service. |
| 10. Optimisation | Capacité admissible au coût moyen minimal | Plusieurs graines, coût horaire et abandon hypothétiques. |
| 11. Résultats | Tableau dans docs/demonstration/scenarios.json et E_capacites.csv | Utiliser les chiffres calculés, conserver les unités et le scénario. |
| 12. Limites et conclusion | Données synthétiques, information parfaite, aucune calibration terrain | Expliquer ce que démontre l'expérimentation et ses limites. |

## Démonstration de cinq minutes

- 0:00 à 0:40 : accueil, question métier et méthode.
- 0:40 à 1:20 : Simulation, réglages, Soutenance reproductible, graine 42, patience 12, deux caisses. Cliquer Voir le pic.
- 1:20 à 2:10 : inspecter un client en file puis ouvrir la caisse 3. Attendre la confirmation Python. Montrer le rang et le journal.
- 2:10 à 3:00 : sélectionner un client encore en file et choisir une autre caisse ouverte. Montrer l'alternative au glisser-déposer.
- 3:00 à 4:10 : Interventions, comparer le bilan au témoin. Puis Laboratoire de décision, cinq graines, cinq caisses, hypothèses par défaut.
- 4:10 à 5:00 : commenter la recommandation conditionnelle, exporter le ZIP, conclure sur les limites.

En cas d'indisponibilité réseau, utiliser l'application locale déjà préparée ou les CSV et le rapport dans docs/demonstration. Les résultats de secours ne remplacent pas une démonstration interactive.

## Questions et réponses

**Pourquoi FIFO ?** C'est la règle dans chaque file. Une réaffectation rejoint la fin de la file cible.

**Pourquoi plusieurs graines ?** Un seul tirage ne permet pas de juger la robustesse. Les capacités d'une graine partagent exactement la même clientèle.

**Les coûts sont-ils réels ?** Non. Mobilisation en caisse-minutes divisée par soixante, multipliée par le coût horaire saisi, plus une hypothèse par abandon.

**Le P90 représente-t-il le maximum ?** Non. C'est le percentile interpolé sous lequel se trouvent environ 90 % des attentes des servis.

**Pourquoi exclure les abandons de la moyenne des servis ?** Leur parcours ne termine pas par un service. Ils restent dans le dénominateur du niveau de service.

**Les dessins modifient-ils les calculs ?** Non. Le lecteur ne décide aucune affectation. Le moteur valide les commandes.

**Est-ce une prévision réelle ?** Non. La projection visuelle extrapole une tendance et le modèle n'est pas calibré sur un magasin.

**Quelle est la contribution de chaque membre ?** Présenter les contributions réellement réalisées et utiliser l'historique Git. Ne pas attribuer artificiellement un module à une personne.

## Répartition orale proposée

Intervenant 1 : contexte et objectifs. Intervenant 2 : méthode et architecture. Intervenant 3 : démonstration. Intervenant 4 : analyses, optimisation et limites. Cette répartition de parole ne constitue pas une attribution du développement.
