from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlatformLink(BaseModel):
    label: str
    url: str
    platform: str


class DelayConfig(BaseModel):
    code: str
    delay_seconds: int


class FunnelStep(BaseModel):
    code: str
    title: str
    body: str
    cta_text: str | None = None
    cta_callback: str | None = None
    platforms: list[PlatformLink] = Field(default_factory=list)
    followups: list[DelayConfig] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FunnelConfig(BaseModel):
    start_video_file_id: str | None = None
    start_video_text: str | None = None
    steps: dict[str, FunnelStep]
    followup_texts: dict[str, str]
    application_followups: list[DelayConfig]
    application_buttons: list[PlatformLink] = Field(default_factory=list)


class LeadBroadcastConfig(BaseModel):
    noon_message: str = ''
    evening_message: str = ''
