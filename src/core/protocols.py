"""Protocol definitions for the review plugin system."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import ReviewRequest, ReviewResult, ShieldResult


@runtime_checkable
class ReviewPlugin(Protocol):
    """Common interface implemented by all review plugins."""

    async def initialize(self, config: object) -> None: ...
    async def execute(self, request: ReviewRequest) -> ReviewResult: ...
    async def shutdown(self) -> None: ...


@runtime_checkable
class SecurityShield(Protocol):
    """Security filtering for inputs and outputs."""

    async def shield_input(self, content: str) -> ShieldResult: ...
    async def shield_output(self, content: str) -> ShieldResult: ...
