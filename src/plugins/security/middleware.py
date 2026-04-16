"""Security middleware injected into all pipelines."""

from __future__ import annotations

from typing import Any, Protocol

import structlog

from core.types import ShieldFinding, ShieldResult

logger = structlog.get_logger()


class _ArmorClientProtocol(Protocol):
    """Internal protocol matching ModelArmorClient and any test fake."""

    async def sanitize_input(self, content: str) -> Any: ...
    async def sanitize_output(self, content: str) -> Any: ...
    async def close(self) -> None: ...


class ModelArmorMiddleware:
    """Security middleware implementing SecurityShield Protocol."""

    def __init__(
        self,
        client: _ArmorClientProtocol,
        block_on_high_severity: bool = True,
        log_findings: bool = True,
    ) -> None:
        self.client = client
        self.block_on_high_severity = block_on_high_severity
        self.log_findings = log_findings

    async def shield_input(self, content: str) -> ShieldResult:
        """Input shield: scan with Model Armor API."""
        response = await self.client.sanitize_input(content)
        findings = self._extract_findings(response)
        blocked = self._should_block(findings)

        if self.log_findings and findings:
            logger.warning(
                "Input shield findings detected",
                finding_count=len(findings),
                blocked=blocked,
            )

        return ShieldResult(
            allowed=not blocked,
            sanitized_content=content if not blocked else "",
            findings=findings,
            raw_response=response,
        )

    async def shield_output(self, content: str) -> ShieldResult:
        """Output shield: prevent sensitive data leakage from LLM responses."""
        response = await self.client.sanitize_output(content)
        findings = self._extract_findings(response)
        blocked = self._should_block(findings)

        if self.log_findings and findings:
            logger.warning(
                "Output shield findings detected",
                finding_count=len(findings),
                blocked=blocked,
            )

        return ShieldResult(
            allowed=not blocked,
            sanitized_content=content if not blocked else "[REDACTED]",
            findings=findings,
            raw_response=response,
        )

    def _should_block(self, findings: list[ShieldFinding]) -> bool:
        if not self.block_on_high_severity:
            return False
        return any(f.severity in ("high", "critical") for f in findings)

    def _extract_findings(self, response: Any) -> list[ShieldFinding]:
        """Convert API response to ShieldFinding list.

        Supports both real SanitizeResponse (Protobuf) and test fakes (dict).
        """
        # 1. Direct findings list (common in tests/fakes)
        findings = self._parse_explicit_findings(response)
        if findings:
            return findings

        # 2. Fallback to sanitization_result (Protobuf responses)
        return self._parse_protobuf_response(response)

    def _parse_explicit_findings(self, response: Any) -> list[ShieldFinding]:
        """Parse explicit findings list from response."""
        findings: list[ShieldFinding] = []
        if not (hasattr(response, "findings") and isinstance(response.findings, list | tuple)):
            return findings

        for item in response.findings:
            category = (
                item.get("category")
                if isinstance(item, dict)
                else getattr(item, "category", None)
            ) or "unknown"
            severity = (
                item.get("severity")
                if isinstance(item, dict)
                else getattr(item, "severity", None)
            ) or "low"
            description = (
                item.get("description")
                if isinstance(item, dict)
                else getattr(item, "description", None)
            ) or ""

            findings.append(
                ShieldFinding(
                    category=category,
                    severity=severity,  # type: ignore[arg-type]
                    description=description,
                )
            )
        return findings

    def _parse_protobuf_response(self, response: Any) -> list[ShieldFinding]:
        """Parse complex Protobuf-style response structure."""
        findings: list[ShieldFinding] = []
        if not hasattr(response, "sanitization_result"):
            return findings

        result = response.sanitization_result
        if hasattr(result, "filter_results"):
            for filter_name, filter_result in result.filter_results.items():
                match_state = getattr(filter_result, "match_state", "NO_MATCH")
                if str(match_state) != "NO_MATCH":
                    findings.append(
                        ShieldFinding(
                            category=filter_name,
                            severity="high",
                            description=f"Filter matched: {filter_name} ({match_state})",
                        )
                    )
        return findings

