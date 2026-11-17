"""Test minimal : le paquet s'importe."""

import queuesmart


def test_package_is_importable() -> None:
    assert queuesmart.__doc__
