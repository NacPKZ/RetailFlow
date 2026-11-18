"""État des files reconstruit en rejouant les événements (rangs, client servi, ouverture)."""


class QueueBoard:
    """Files FIFO par caisse, telles qu'elles sont après chaque événement.

    Le ``queue_position`` des événements n'est pas fiable pour tous les cas
    (départs, abandons, changements) : les rangs sont donc recalculés ici.
    """

    def __init__(self, register_count: int, initially_open: int) -> None:
        self._waiting: dict[int, list[int]] = {rid: [] for rid in range(1, register_count + 1)}
        self._serving: dict[int, int | None] = dict.fromkeys(self._waiting)
        self._open = {rid: rid <= initially_open for rid in self._waiting}

    def waiting(self, register_id: int) -> tuple[int, ...]:
        """Clients en attente à cette caisse, tête de file en premier."""
        return tuple(self._waiting[register_id])

    def rank(self, register_id: int, customer_id: int) -> int:
        """Rang du client dans la file (1 = tête)."""
        return self._waiting[register_id].index(customer_id) + 1

    def serving(self, register_id: int) -> int | None:
        return self._serving[register_id]

    def is_open(self, register_id: int) -> bool:
        return self._open[register_id]

    def join(self, register_id: int, customer_id: int) -> None:
        self._waiting[register_id].append(customer_id)

    def leave(self, register_id: int, customer_id: int) -> None:
        """Retire un client de la file (service, abandon ou changement de file)."""
        if customer_id not in self._waiting[register_id]:
            raise ValueError(f"Client {customer_id} absent de la file de la caisse {register_id}.")
        self._waiting[register_id].remove(customer_id)

    def start_service(self, register_id: int, customer_id: int) -> None:
        self.leave(register_id, customer_id)
        self._serving[register_id] = customer_id

    def end_service(self, register_id: int) -> None:
        self._serving[register_id] = None

    def set_open(self, register_id: int, is_open: bool) -> None:
        self._open[register_id] = is_open
