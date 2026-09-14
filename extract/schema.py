"""Strict output contract for one posting's extraction."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SECTION = Literal["responsibility", "requirement", "nice_to_have"]
SENIORITY = Literal["junior", "mid", "senior", "staff_plus", "unspecified"]
TRAVEL = Literal["none", "occasional", "frequent", "unspecified"]


class SkillMention(BaseModel):
    canonical: str
    section: SECTION
    evidence: str = Field(max_length=120)


class Extraction(BaseModel):
    posting_id: str
    skills: list[SkillMention]
    seniority: SENIORITY
    years_required: int | None = None
    travel_expectation: TRAVEL
    customer_facing_intensity: int = Field(ge=1, le=5)
    responsibility_verbs: list[str] = Field(min_length=5, max_length=5)
    segmentation_quality: Literal["header", "inferred"]


def json_schema() -> dict:
    return Extraction.model_json_schema()
