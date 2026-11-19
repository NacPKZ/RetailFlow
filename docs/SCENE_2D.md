# RetailFlow | Scène 2D interactive

Dans `app.py`, ouvrez **Simulation**, puis **Magasin**. Le composant `frontend_studio` rejoue le journal du moteur dynamique. Le rejeu FIFO et l’écran client historique sont accessibles dans Simulation.

## Piloter le magasin

- Lancez, mettez en pause ou changez la vitesse. **Voir le pic** place le curseur au pic calculé.
- Zoomez, recentrez, passez en plein écran ou utilisez la mini-carte et le suivi de client.
- Cliquez sur une caisse pour changer son état. Une caisse fermée termine son service en cours et sa file est réaffectée aux caisses ouvertes.
- Sélectionnez un client en attente, inspectez son parcours puis réaffectez-le à une caisse ouverte. Sa patience et son arrivée sont conservées. La dernière caisse ouverte est protégée.
- Utilisez **Analyser ce scénario**, puis **Interventions**, pour voir le bilan apparié. Les exports d’instant et d’image restent dans la scène.

Les trajectoires représentent une ligne par caisse, jusqu’à six sprites visibles et un compteur de surplus. Les changements de caméra et les pulsations de caisse utilisent la boucle Canvas existante. Les effets décoratifs respectent le contrôle de la scène et la préférence système de mouvement réduit.

Les paramètres et actions validées sont conservés pendant la navigation. Python calcule les interventions à la minute du geste. La vitesse de lecture ne modifie aucun événement. Les courses dessinées sont illustratives et les clients peuvent se croiser dans les allées.

| Élément | Responsabilité |
| --- | --- |
| `queuesmart/simulation/dynamic.py` | Événements, affectations, services et interventions |
| `queuesmart/scene/timeline.py` | Trajectoires, places de file et états visuels en Python |
| `queuesmart/ui/studio_component.py` | Transmission des résultats et réception des actions dans Streamlit |
| `frontend_studio/` | Commandes, lecture temporelle et interpolation Canvas |
| `queuesmart/analytics/dynamic_kpi.py` | Séries analytiques à partir du même journal |

`frontend_2d/` et `dynamic_demo.py` restent disponibles pour les bancs d’essai de la première scène.
