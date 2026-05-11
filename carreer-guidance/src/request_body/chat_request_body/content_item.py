from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class ContentItem(BaseModel):
    """A single chat response item that can be text or image."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["text", "image"]
    text: str | None = None
    image_url: str | None = None

    @model_validator(mode="after")
    def validate_content_by_type(self) -> "ContentItem":
        if self.type == "text" and not self.text:
            raise ValueError("text is required when type='text'")
        if self.type == "text" and self.image_url is not None:
            raise ValueError("image_url must be None when type='text'")
        if self.type == "image" and self.image_url is None:
            raise ValueError("image_url is required when type='image'")
        if self.type == "image" and self.text is not None:
            raise ValueError("text must be None when type='image'")
        if self.type == "image" and self.image_url:
            url = self.image_url.strip()
            if not (
                url.startswith("/")
                or url.startswith("http://")
                or url.startswith("https://")
            ):
                raise ValueError("image_url must be absolute or root-relative")
            self.image_url = url
        return self
