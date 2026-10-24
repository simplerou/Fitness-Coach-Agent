from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator


class KnowledgeMetadata(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    source_name: str | None = Field(default=None, max_length=180)
    source_url: str | None = Field(default=None, max_length=2000)

    @field_validator("title", "source_name", "source_url")
    @classmethod
    def trim(cls, value):
        return value.strip() or None if value is not None else None

    @field_validator("source_url")
    @classmethod
    def valid_url(cls, value):
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("资料链接必须是有效的 http 或 https 地址。")
        return value


class KnowledgeIndexRequest(BaseModel):
    cloud_consent: Literal[True]
