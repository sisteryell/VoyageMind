"""
schemas.py — Data shapes (Pydantic models)

Pydantic models do two things at once:
  1. They describe the shape of data (what fields exist, what types they are).
  2. They validate data automatically — if the data doesn't match, Pydantic
     raises a clear error instead of letting bad data flow through the app.

This file contains:
  - Agent output models     — CityRecommendation, FinalRecommendation, Itinerary
  - API request / response  — PlanRequest, ChatRequest, CompareRequest, etc.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------

def _validate_country(v: str) -> str:
    """Reusable country-name sanitiser used by multiple request models."""
    v = v.strip()
    if len(v) < 2:
        raise ValueError("Country name must be at least 2 characters")
    if re.search(r"[<>{}\[\];]", v):
        raise ValueError("Country name contains invalid characters")
    if not re.search(r"[a-zA-Z]", v):
        raise ValueError("Country name must contain letters")
    return v


# ---------------------------------------------------------------------------
# Models used internally by the AI agents
# ---------------------------------------------------------------------------

class CityRecommendation(BaseModel):
    """One city suggested by a specialist agent, with a score and reason."""

    city: str = Field(..., description="City name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0-1")
    reason: str = Field(..., description="Why this city was chosen")

    @field_validator("city", "reason")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class CityRecommendationList(BaseModel):
    """Exactly 3 city recommendations — the output of one specialist agent."""

    recommendations: list[CityRecommendation] = Field(..., min_length=3, max_length=3)

    @classmethod
    def from_list(cls, data: list) -> CityRecommendationList:
        return cls(recommendations=[CityRecommendation(**item) for item in data])


class FinalRecommendation(BaseModel):
    """One city in the final top-2 output from the aggregator agent."""

    city: str = Field(..., description="City name")
    reason: str = Field(..., description="Combined justification from all agents")

    @field_validator("city", "reason")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class FinalRecommendationList(BaseModel):
    """Exactly 2 final city recommendations — the aggregator's output."""

    recommendations: list[FinalRecommendation] = Field(..., min_length=2, max_length=2)

    @classmethod
    def from_list(cls, data: list) -> FinalRecommendationList:
        return cls(recommendations=[FinalRecommendation(**item) for item in data])


# ---------------------------------------------------------------------------
# Itinerary models — output of the ItineraryAgent
# ---------------------------------------------------------------------------

class DayPlan(BaseModel):
    """One day's plan inside a city itinerary."""

    day: int = Field(..., ge=1, description="Day number")
    title: str = Field(..., description="Theme for the day")
    activities: list[str] = Field(..., min_length=1, description="List of activities")


class Itinerary(BaseModel):
    """A full day-by-day itinerary for one city."""

    days: list[DayPlan] = Field(..., min_length=1)

    @classmethod
    def from_list(cls, data: list) -> Itinerary:
        return cls(days=[DayPlan(**d) for d in data])


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

VALID_BUDGETS = ("budget", "mid", "luxury")
VALID_STYLES = ("adventure", "relaxation", "family", "honeymoon", "solo", "culture", "food", "nature")


class PlanRequest(BaseModel):
    """POST /plan — the JSON body sent by the browser."""

    country: str = Field(..., min_length=1, max_length=100, description="Country to explore")
    budget: str = Field("mid", description="budget | mid | luxury")
    duration: int = Field(5, ge=1, le=30, description="Trip length in days")
    travel_styles: list[str] = Field(default_factory=list, description="e.g. adventure, family")
    session_id: str | None = Field(default=None, description="Optional session ID")

    @field_validator("country")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)

    @field_validator("budget")
    @classmethod
    def valid_budget(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_BUDGETS:
            raise ValueError(f"Budget must be one of: {', '.join(VALID_BUDGETS)}")
        return v

    @field_validator("travel_styles")
    @classmethod
    def valid_styles(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip().lower() for s in v if s.strip()]
        invalid = [s for s in cleaned if s not in VALID_STYLES]
        if invalid:
            raise ValueError(f"Invalid travel styles: {invalid}. Choose from: {', '.join(VALID_STYLES)}")
        return cleaned


class PlanResponse(BaseModel):
    """POST /plan — the JSON body returned to the browser."""

    country: str
    budget: str
    duration: int
    travel_styles: list[str]
    recommendations: list[dict]
    itineraries: list[dict]
    agent_details: dict
    session_id: str


class ChatRequest(BaseModel):
    """POST /chat — follow-up question about a previous plan."""

    country: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=500, description="The user's question")
    budget: str = Field("mid")
    duration: int = Field(5, ge=1, le=30)
    travel_styles: list[str] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list, description="Previous plan results for context")

    @field_validator("country")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)


class ChatResponse(BaseModel):
    """POST /chat — the assistant's answer."""

    answer: str


class CompareRequest(BaseModel):
    """POST /compare — compare two countries side by side."""

    country_a: str = Field(..., min_length=1, max_length=100)
    country_b: str = Field(..., min_length=1, max_length=100)
    budget: str = Field("mid")
    duration: int = Field(5, ge=1, le=30)
    travel_styles: list[str] = Field(default_factory=list)

    @field_validator("country_a", "country_b")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)
