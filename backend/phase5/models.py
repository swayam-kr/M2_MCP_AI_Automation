"""
Phase 5: Pydantic Request/Response Models
==========================================
Defines exact shapes for all FastAPI endpoint contracts.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ── Part A: Weekly Review Pulse ──────────────────────────────

class PulseRequest(BaseModel):
    weeks: int = Field(default=4, ge=1, le=8, description="Number of weeks to analyze")
    max_reviews: int = Field(default=100, ge=10, le=200, description="Max reviews to process")
    star_range_min: int = Field(default=1, ge=1, le=5, description="Min star filter")
    star_range_max: int = Field(default=5, ge=1, le=5, description="Max star filter")


class PulseQuote(BaseModel):
    text: str
    star_rating: int
    date: str


class PulseData(BaseModel):
    generated_at: str
    provider_used: str
    period: str
    analysis_explanation: str
    total_reviews_analyzed: int
    themes: List[Dict[str, Any]]
    top_3_themes: List[str]
    quotes: List[PulseQuote]
    summary: str
    action_ideas: List[str]


class PulseResponse(BaseModel):
    status: str
    provider_used: Optional[str] = None
    latency_ms: Optional[int] = None
    data: Optional[PulseData] = None
    error: Optional[str] = None


# ── Part B: Fee Explainer ────────────────────────────────────

class ExplainerRequest(BaseModel):
    asset_class: str = Field(..., description="Stocks / F&O / Mutual Funds")


class ExplainerData(BaseModel):
    generated_at: str
    asset_class: str
    explanation_bullets: List[str]
    tone: str
    official_links: List[str]
    last_checked: str
    provider_used: str


class ExplainerResponse(BaseModel):
    status: str
    provider_used: Optional[str] = None
    latency_ms: Optional[int] = None
    data: Optional[ExplainerData] = None
    error: Optional[str] = None


# ── Part C: MCP Dispatch ────────────────────────────────────

class DispatchApprovals(BaseModel):
    append_to_doc: bool = False
    create_draft: bool = False


class DispatchRequest(BaseModel):
    content_type: str = Field(..., description="pulse, explainer, or combined")
    content: Dict[str, Any] = Field(..., description="Generated JSON content")
    approvals: DispatchApprovals
    recipients: List[str] = Field(default_factory=list)


class GateStatus(BaseModel):
    status: str  # "appended" / "created" / "sent" / "skipped" / "error"
    error: Optional[str] = None


class DispatchResults(BaseModel):
    doc: GateStatus
    draft: GateStatus


class DispatchResponse(BaseModel):
    status: str
    results: Optional[DispatchResults] = None
    error: Optional[str] = None
