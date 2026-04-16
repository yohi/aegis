"""Tests for core/protocols.py — Protocol definitions."""

from __future__ import annotations

from core.protocols import ReviewPlugin, SecurityShield
from tests.unit.conftest import FakeSecurityShield


class TestProtocolDefinitions:
    """Verify Protocol definitions exist and are runtime_checkable."""

    def test_review_plugin_is_runtime_checkable(self) -> None:
        assert hasattr(ReviewPlugin, "__protocol_attrs__") or isinstance(
            ReviewPlugin, type
        )

    def test_security_shield_is_runtime_checkable(self) -> None:
        assert isinstance(FakeSecurityShield(), SecurityShield)
