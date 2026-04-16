"""Google Cloud Model Armor API client."""

from __future__ import annotations

from typing import Any


class ModelArmorClient:
    """Google Cloud Model Armor API client.

    In production, this wraps google.cloud.modelarmor_v1.ModelArmorAsyncClient.
    The interface is designed for dependency injection / test replacement.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        template_id: str = "default-shield",
    ) -> None:
        self.project_id = project_id
        self.location = location
        self.template_id = template_id
        self._client: Any | None = None

    @property
    def _template_name(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}/templates/{self.template_id}"

    async def _get_client(self) -> Any:
        """Lazy initialization to obtain client."""
        if self._client is None:
            try:
                from google.cloud.modelarmor_v1 import ModelArmorAsyncClient

                self._client = ModelArmorAsyncClient()
            except ImportError as exc:
                raise ImportError(
                    "google-cloud-modelarmor is required. "
                    "Install with: pip install google-cloud-modelarmor"
                ) from exc
        return self._client

    async def sanitize_input(self, content: str) -> Any:
        """Scan input content with Model Armor."""
        client = await self._get_client()
        from google.cloud.modelarmor_v1 import SanitizeUserPromptRequest

        # Use dictionary for data to bypass missing class names in older/different SDK versions
        request = SanitizeUserPromptRequest(
            name=self._template_name,
            user_prompt_data={"text": content},
        )
        return await client.sanitize_user_prompt(request=request)

    async def sanitize_output(self, content: str) -> Any:
        """Scan LLM output with Model Armor (data leak prevention)."""
        client = await self._get_client()
        from google.cloud.modelarmor_v1 import SanitizeModelResponseRequest

        request = SanitizeModelResponseRequest(
            name=self._template_name,
            model_response_data={"text": content},
        )
        return await client.sanitize_model_response(request=request)

    async def close(self) -> None:
        """Release client resources."""
        if self._client is not None:
            if hasattr(self._client, "close"):
                await self._client.close()
            self._client = None
