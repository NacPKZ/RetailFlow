# Exemples Clean Code : avant / après

> **Origine des exemples.** Le moteur a d'abord été écrit volontairement sous une forme
> naïve (une seule fonction `run`), puis exécuté sur les 3 scénarios. Il a ensuite été
> refactoré en classes. Le projet n'utilisant pas encore git, la version naïve est
> conservée ci-dessous telle qu'elle a été écrite.
> **Preuve que le comportement est préservé** : avec la graine 42, les deux versions
> donnent exactement les mêmes attentes moyennes (par exemple 2,25 min puis 1,91 min
> à l'heure de pointe), et `pytest` passe sur la version refactorée.

## La version naïve d'origine (`queuesmart/simulation/engine.py`, première version)

```python
def run(config, strategy):
    rng = random.Random(config.seed)
    arrivals = sorted(rng.uniform(0, config.arrival_window_min) for _ in range(config.customer_count))
    customers = []
    for i, a in enumerate(arrivals):
        d = rng.gammavariate(2.0, config.mean_service_time_min / 2.0)
        if d < 0.3:
            d = 0.3
        customers.append(Customer(i + 1, a, d))
    registers = [CheckoutRegister(i + 1) for i in range(config.open_registers)]
    for c in customers:
        best = None
        for r in registers:
            if strategy == "shortest_queue":
                if best is None or r.queue_length_at(c.arrival_time) < best.queue_length_at(c.arrival_time):
                    best = r
            elif strategy == "least_wait":
                if best is None or r.estimated_wait_at(c.arrival_time) < best.estimated_wait_at(c.arrival_time):
                    best = r
            else:
                raise Exception("bad strategy")
        best.serve(c)
    return SimulationResult(config, strategy, tuple(customers), tuple(registers))
```

Les défauts : une fonction de 25 lignes qui fait trois choses, des `if/elif` sur des chaînes,
des nombres magiques (`2.0`, `0.3`), des noms d'une lettre (`a`, `d`, `c`, `r`), une
`Exception` générique avec un message en anglais et l'absence de type hints et de docstring.

---

## Exemple 1 : responsabilité unique (SRP), découpage en Generator, Strategy et Engine

**Avant** : `run()` génère les clients, choisit les caisses **et** orchestre la simulation.
Pour tester la génération seule, il faut lancer toute la simulation.

**Après** : chaque responsabilité a sa classe, et le moteur se contente d'orchestrer.

```python
class SimulationEngine:
    def __init__(self, strategy: AssignmentStrategy) -> None:
        self._strategy = strategy

    def run(self, config: ScenarioConfig) -> SimulationResult:
        """Simule un scénario complet et renvoie un résultat immuable."""
        customers = CustomerGenerator(config).generate()
        registers = [
            CheckoutRegister(register_id) for register_id in range(1, config.open_registers + 1)
        ]
        for customer in customers:
            chosen = self._strategy.choose(registers, customer.arrival_time)
            chosen.serve(customer)
        return SimulationResult(config, self._strategy.name, tuple(customers), tuple(registers))
```

**Gain** : `CustomerGenerator` a ses propres tests (taille, tri, bornes, reproductibilité,
moyenne). Le moteur lit comme une phrase.

## Exemple 2 : polymorphisme et registre au lieu de `if/elif`

**Avant** : chaque nouveau comportement oblige à ajouter un `elif` **dans la boucle du moteur**,
ce qui viole le principe ouvert/fermé. Le code de départage (`best is None or … < …`) est dupliqué.

**Après** (`queuesmart/simulation/strategies.py`) :

```python
class ShortestQueueStrategy(AssignmentStrategy):
    name = "shortest_queue"
    label = "File la plus courte"

    def choose(self, registers, time):
        return _lowest(registers, lambda register: register.queue_length_at(time))


class LeastWaitStrategy(AssignmentStrategy):
    name = "least_wait"
    label = "Attente estimée minimale (écran client)"

    def choose(self, registers, time):
        return _lowest(registers, lambda register: register.estimated_wait_at(time))


STRATEGIES = {strategy.name: strategy for strategy in (ShortestQueueStrategy, LeastWaitStrategy)}

def build_strategy(name: str) -> AssignmentStrategy:
    try:
        return STRATEGIES[name]()
    except KeyError:
        raise UnknownStrategyError(f"Comportement client inconnu : « {name} ». …") from None
```

**Gain** : ajouter un comportement revient à écrire une classe et à l'ajouter au registre.
Le moteur, la barre latérale (qui affiche `label`) et le dashboard ne changent pas.
La règle d'égalité (la caisse au plus petit numéro) est écrite **une seule fois** dans `_lowest` (DRY).
L'erreur est typée et son message est en français.

## Exemple 3 : nombres magiques remplacés par des constantes nommées dans `config.py`

**Avant** :

```python
d = rng.gammavariate(2.0, config.mean_service_time_min / 2.0)
if d < 0.3:
    d = 0.3
```

Que signifient `2.0` et `0.3` ? Et si on change la forme, faut-il penser à modifier
**les deux** `2.0` ?

**Après** (`queuesmart/config.py` et `queuesmart/simulation/generator.py`) :

```python
MIN_SERVICE_TIME_MIN = 0.3  # plancher : même un client pressé prend ~20 s
SERVICE_TIME_SHAPE = 2.0    # forme de la loi gamma (dispersion modérée)

def _service_duration(self, rng: random.Random) -> float:
    # Loi gamma : moyenne = forme x échelle, donc échelle = moyenne / forme.
    scale = self._config.mean_service_time_min / SERVICE_TIME_SHAPE
    return max(MIN_SERVICE_TIME_MIN, rng.gammavariate(SERVICE_TIME_SHAPE, scale))
```

**Gain** : le sens est explicite, la valeur est modifiable à un seul endroit, et le même
`MIN_SERVICE_TIME_MIN` sert aussi à la validation de `ScenarioConfig` et à la borne du
slider de la barre latérale.

## Exemple 4 : logique sortie du code de rendu pour être testable (SRP)

**Avant** : la première version de `queuesmart/ui/store_view.py` contenait la légende du client suivi,
une fonction privée mêlée au code Plotly, que l'on ne pouvait tester qu'en lançant Streamlit :

```python
# queuesmart/ui/store_view.py (première version)
def _status(customer: Customer, time: float) -> str:
    """Situation du client suivi, en clair."""
    if time < customer.arrival_time:
        return "pas encore arrivé"
    if customer.is_waiting_at(time):
        return f"en file depuis {format_minutes(time - customer.arrival_time)}"
    if customer.is_being_served_at(time):
        return f"en caisse {customer.register_id} (a attendu {format_minutes(customer.wait_time)})"
    return f"parti (a attendu {format_minutes(customer.wait_time)})"
```

**Après** : la fonction devient publique, `describe_status`, dans le module pur `store_layout.py`.
On en profite pour retirer le double appel à `format_minutes(customer.wait_time)` (DRY) :

```python
# queuesmart/ui/store_layout.py
def describe_status(customer: Customer, time: float) -> str:
    """Situation d'un client à l'instant ``time``, en clair (légende du client suivi)."""
    if time < customer.arrival_time:
        return "pas encore arrivé"
    if customer.is_waiting_at(time):
        return f"en file depuis {format_minutes(time - customer.arrival_time)}"
    waited = format_minutes(customer.wait_time)
    if customer.is_being_served_at(time):
        return f"en caisse {customer.register_id} (a attendu {waited})"
    return f"parti (a attendu {waited})"
```

**Gain** : les 4 états sont testés en quelques millisecondes (`tests/test_store_layout.py`),
et `store_view.py` ne fait plus que dessiner. La même opération a été faite pour
`animation_step` (calcul du pas d'animation).

---

## À compléter par le groupe

Ajoutez ici les vrais refactorings faits pendant les relectures de Pull Requests, avec leur
version « avant » **uniquement si elle a réellement existé**. Pour la soutenance, vous pouvez
aussi citer ces choix de conception, sans les présenter comme des refactorings :

- `format_minutes` est l'unique formatage des durées, utilisé par les 3 onglets (DRY) ;
- `Customer.wait_time` est l'unique définition de l'attente (DRY).
