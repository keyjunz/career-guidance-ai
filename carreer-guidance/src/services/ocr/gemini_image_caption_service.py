import base64
import logging
import os
from pathlib import Path

import google.generativeai as genai

from src.config.settings_models import get_settings
from src.prompts.ocr_prompt import GEMINI_IMAGE_CAPTION_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GeminiImageCaptionService:
    """Generate concise captions for images using Gemini Vision."""

    def __init__(
        self,
        execution_id: str,
        model_name: str | None = None,
        api_key: str | None = None,
        timeout_s: int | None = None,
    ) -> None:
        self.execution_id = execution_id
        settings_api_key = ""
        settings_model_name = ""
        try:
            settings = get_settings()
            settings_api_key = str(settings.llm.gemini_api_key or "").strip()
            settings_model_name = str(settings.llm.gemini_model_name or "").strip()
        except Exception:
            logger.warning(
                "Gemini captioner cannot load settings for execution_id=%s. Falling back to environment variables.",
                self.execution_id,
            )

        self.model_name = (
            model_name
            or os.getenv("GEMINI_IMAGE_CAPTION_MODEL_NAME", "").strip()
            or settings_model_name
            or os.getenv("GEMINI_MODEL_NAME", "").strip()
        )
        self.api_key = (
            api_key
            or settings_api_key
            or os.getenv("GEMINI_IMAGE_CAPTION_API_KEY", "").strip()
            or os.getenv("GEMINI_API_KEY", "").strip()
        )
        self.timeout_s = timeout_s or int(
            os.getenv("GEMINI_IMAGE_CAPTION_TIMEOUT", "60")
        )

        if not self.api_key:
            raise ValueError(
                "Gemini caption API key is missing. Set GEMINI_IMAGE_CAPTION_API_KEY (or GEMINI_API_KEY)."
            )
        if not self.model_name:
            raise ValueError(
                "GEMINI_IMAGE_CAPTION_MODEL_NAME or GEMINI_MODEL_NAME is required"
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def caption_image(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image_bytes = path.read_bytes()
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = self._guess_mime_type(path)

        response = self.model.generate_content(
            [
                GEMINI_IMAGE_CAPTION_PROMPT,
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": encoded,
                    }
                },
            ],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 128,
            },
        )
        return str(getattr(response, "text", "") or "").strip()

    def _guess_mime_type(self, path: Path) -> str:
        suffix = path.suffix.lower().strip(".")
        if suffix in {"jpg", "jpeg"}:
            return "image/jpeg"
        if suffix == "webp":
            return "image/webp"
        return "image/png"
