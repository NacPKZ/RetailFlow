"""Erreurs métier de QueueSmart.

Toutes héritent de ``QueueSmartError`` : l'interface peut ainsi attraper
les erreurs « attendues » sans masquer les vrais bugs (``except Exception``).
Les arguments invalides de méthodes utilitaires lèvent ``ValueError``.
"""


class QueueSmartError(Exception):
    """Base de toutes les erreurs métier du projet."""


class InvalidScenarioError(QueueSmartError):
    """Paramètres de scénario incohérents (nombre de clients, de caisses…)."""


class InvalidAssignmentError(QueueSmartError):
    """Affectation d'un client impossible (déjà affecté, servi avant d'arriver)."""


class CustomerNotServedError(QueueSmartError):
    """Information demandée sur un client qui n'a pas encore été affecté."""


class UnknownCustomerError(QueueSmartError):
    """Identifiant de client absent de la simulation."""


class UnknownStrategyError(QueueSmartError):
    """Nom de comportement client (stratégie) inconnu."""
