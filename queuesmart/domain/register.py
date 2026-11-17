"""Caisse du supermarché et sa file d'attente FIFO."""

from queuesmart.domain.customer import Customer


class CheckoutRegister:
    """Une caisse : elle sert ses clients un par un, dans l'ordre d'arrivée (FIFO).

    La liste des clients est encapsulée : on ne peut l'alimenter que via ``serve``,
    ce qui garantit l'absence de chevauchement entre deux services.
    """

    def __init__(self, register_id: int) -> None:
        self._register_id = register_id
        self._customers: list[Customer] = []

    @property
    def register_id(self) -> int:
        return self._register_id

    @property
    def customers(self) -> tuple[Customer, ...]:
        """Clients affectés à cette caisse, dans l'ordre de service (lecture seule)."""
        return tuple(self._customers)

    @property
    def busy_until(self) -> float:
        """Instant où la caisse aura fini de servir tous ses clients actuels."""
        return self._customers[-1].service_end if self._customers else 0.0

    def serve(self, customer: Customer) -> None:
        """Ajoute le client en fin de file : il commence dès que la caisse est libre."""
        service_start = max(customer.arrival_time, self.busy_until)
        customer.assign(self._register_id, service_start)
        self._customers.append(customer)

    def queue_length_at(self, time: float) -> int:
        """Nombre de clients présents à la caisse à l'instant ``time`` (service compris).

        C'est ce que voit un client qui choisit « la file la plus courte ».
        """
        return sum(1 for customer in self._customers if customer.is_present_at(time))

    def estimated_wait_at(self, time: float) -> float:
        """Attente d'un client qui rejoindrait la file à l'instant ``time``.

        Seuls les clients déjà arrivés (arrivée <= time) comptent : l'écran ne
        connaît pas l'avenir. Il connaît en revanche le travail restant de chacun
        (hypothèse documentée : estimation parfaite, ex. à partir des articles).
        """
        arrived = [customer for customer in self._customers if customer.arrival_time <= time]
        if not arrived:
            return 0.0
        return max(0.0, arrived[-1].service_end - time)

    def busy_time(self) -> float:
        """Durée totale pendant laquelle la caisse a servi des clients."""
        return sum(customer.service_duration for customer in self._customers)
