from typing import Literal

from pydantic import BaseModel, Field

FixtureId = Literal["exact_headers", "common_aliases", "missing_email"]
TargetField = Literal[
    "external_id", "email", "first_name", "last_name", "phone", "signup_date"
]

REQUIRED_TARGET_FIELDS: tuple[TargetField, ...] = ("external_id", "email")


class PreviewRequest(BaseModel):
    fixture_id: FixtureId


class ToolRequest(BaseModel):
    tool: Literal["inspect_import_context"]
    fixture_id: FixtureId


class FieldMapping(BaseModel):
    source_field: str
    target_field: TargetField
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class MappingProposal(BaseModel):
    mappings: list[FieldMapping]
    unmapped_required_fields: list[TargetField]
    warnings: list[str]
    recommendation: Literal["ready_for_review", "blocked"]


class PreviewResponse(BaseModel):
    fixture_id: FixtureId
    decision: Literal["proposal", "blocked"]
    proposal: MappingProposal | None = None
    blocked_reason: str | None = None
