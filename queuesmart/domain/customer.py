"""Client du supermarché."""

from dataclasses import dataclass

from queuesmart.exceptions import CustomerNotServedError, InvalidAssignmentError


@dataclass
class Customer:
    """Un client : il arrive, attend dans une file, puis est servi à une caisse.

    Tous les temps sont en minutes depuis l'ouverture. Tant que le client n'est
    pas affecté (``assign``), sa fin de service et son attente sont inconnues.
    """

    customer_id: int
    arrival_time: float
    service_duration: float
    register_id: int | None = None
    service_start: float | None = None

    def assign(self, register_id: int, service_start: float) -> None:
        """Affecte le client à une caisse, une seule fois et jamais avant son arrivée."""
        if self.is_served:
            raise InvalidAssignmentError(
                f"Le client {self.customer_id} est déjà affecté à la caisse {self.register_id}."
            )
        if service_start < self.arrival_time:
            raise InvalidAssignmentError(
                f"Le client {self.customer_id} ne peut pas être servi avant son arrivée."
            )
        self.register_id = register_id
        self.service_start = service_start

    @property
    def is_served(self) -> bool:
        """Vrai dès que le client a une caisse et une heure de début de service."""
        return self.service_start is not None

    @property
    def service_end(self) -> float:
        """Instant où le client quitte la caisse."""
        return self._require_service_start() + self.service_duration

    @property
    def wait_time(self) -> float:
        """Temps passé dans la file avant d'être servi (seule définition du projet : DRY)."""
        return self._require_service_start() - self.arrival_time

    def is_waiting_at(self, time: float) -> bool:
        """Le client est arrivé mais n'est pas encore servi."""
        has_arrived = self.arrival_time <= time
        return has_arrived and (not self.is_served or time < self.service_start)

    def is_being_served_at(self, time: float) -> bool:
        """Le client est à la caisse, en train de payer."""
        return self.is_served and self.service_start <= time < self.service_end

    def is_present_at(self, time: float) -> bool:
        """Le client est dans le magasin, côté caisses (en attente ou en service)."""
        return self.is_waiting_at(time) or self.is_being_served_at(time)

    def _require_service_start(self) -> float:
        if self.service_start is None:
            raise CustomerNotServedError(
                f"Le client {self.customer_id} n'a pas encore été affecté à une caisse."
            )
        return self.service_start
