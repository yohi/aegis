"""Tests for core/protocols.py — Protocol definitions."""

from __future__ import annotations

from core.protocols import ReviewPlugin, SecurityShield
from tests.unit.conftest import FakeSecurityShield


class TestProtocolDefinitions:
    """Verify Protocol definitions exist and are runtime_checkable."""

    def test_review_plugin_is_runtime_checkable(self) -> None:
        class ConcretePlugin:
            async def initialize(self, config: object) -> None: ...
            async def execute(self, request: object) -> object: ...
            async def shutdown(self) -> None: ...

        assert isinstance(ConcretePlugin(), ReviewPlugin)

    def test_security_shield_is_runtime_checkable(self) -> None:
        assert isinstance(FakeSecurityShield(), SecurityShield)
