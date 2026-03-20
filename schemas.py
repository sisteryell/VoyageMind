"""Pydantic schemas for request validation, response serialization, and domain models.

All user-facing request models inherit from TravelRequestBase which centralizes
shared field validation (budget, duration, travel_styles) in one place — keeping
validators DRY and consistent across endpoints.
"""

from __future__ import annotations

import re
from enum import Enum
from functools import lru_cache

import pycountry
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Country resolution helpers
# ---------------------------------------------------------------------------

COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US",
    "u.s.a": "US",
    "u.s": "US",
    "us": "US",
    "uk": "GB",
    "u.k": "GB",
    "uae": "AE",
    "south korea": "KR",
    "north korea": "KP",
}


def _normalize_country_key(value: str) -> str:
    """Collapse whitespace, lowercase, and strip dots for fuzzy matching."""
    cleaned = value.strip().lower().replace(".", "")
    return re.sub(r"\s+", " ", cleaned)


@lru_cache
def _country_index() -> dict[str, str]:
    """Build a one-time lookup of every pycountry name/code → canonical name."""
    index: dict[str, str] = {}
    for country in pycountry.countries:
        canonical = country.name
        values = [
            getattr(country, "name", ""),
            getattr(country, "official_name", ""),
            getattr(country, "common_name", ""),
            getattr(country, "alpha_2", ""),
            getattr(country, "alpha_3", ""),
        ]
        for value in values:
            if value:
                index[_normalize_country_key(value)] = canonical
    return index


def _resolve_country(value: str) -> str | None:
    """Map a user-supplied country string to its canonical pycountry name."""
    key = _normalize_country_key(value)
    alias = COUNTRY_ALIASES.get(key)
    if alias:
        key = _normalize_country_key(alias)
    index = _country_index()
    if key in index:
        return index[key]

    try:
        return pycountry.countries.search_fuzzy(value)[0].name
    except LookupError:
        return None


def _validate_country(v: str) -> str:
    """Sanitize and resolve a country name; raises ValueError if unrecognized."""
    v = " ".join(v.strip().split())
    if len(v) < 2:
        raise ValueError("Country name must be at least 2 characters")
    if re.search(r"[<>{}\[\];]", v):
        raise ValueError("Country name contains invalid characters")
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ .'-]+", v):
        raise ValueError("Country name can only contain letters, spaces, apostrophes, dots, and hyphens")
    if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", v):
        raise ValueError("Country name must contain letters")

    resolved = _resolve_country(v)
    if not resolved:
        raise ValueError("Please enter a valid country name")
    return resolved


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Budget(str, Enum):
    """Allowed budget tiers."""
    budget = "budget"
    mid = "mid"
    luxury = "luxury"


class TravelStyle(str, Enum):
    """Specialist agent travel styles available for planning."""
    adventure = "adventure"
    relaxation = "relaxation"
    family = "family"
    honeymoon = "honeymoon"
    solo = "solo"
    culture = "culture"
    food = "food"
    nature = "nature"


# ---------------------------------------------------------------------------
# Reusable validation functions
# ---------------------------------------------------------------------------

def _validate_budget(v: str) -> str:
    """Normalize and validate a budget string against the Budget enum."""
    v = v.strip().lower()
    try:
        return Budget(v).value
    except ValueError:
        raise ValueError(f"Budget must be one of: {', '.join(b.value for b in Budget)}")


def _validate_travel_styles(v: list[str]) -> list[str]:
    """Normalize and validate a list of travel style strings."""
    cleaned = [s.strip().lower() for s in v if s.strip()]
    allowed_values = {style.value for style in TravelStyle}
    invalid = [s for s in cleaned if s not in allowed_values]
    if invalid:
        raise ValueError(
            f"Invalid travel styles: {invalid}. "
            f"Choose from: {', '.join(s.value for s in TravelStyle)}"
        )
    return cleaned


# ---------------------------------------------------------------------------
# Domain models — city recommendations and itineraries
# ---------------------------------------------------------------------------

class _CityBase(BaseModel):
    """Shared base for models that carry a city name and a reason string."""
    city: str = Field(...)
    reason: str = Field(...)

    @field_validator("city", "reason")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class CityRecommendation(_CityBase):
    """A single city recommendation from a specialist travel agent."""
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class CityRecommendationList(BaseModel):
    """Wrapper around a list of specialist-agent city recommendations."""
    recommendations: list[CityRecommendation] = Field(..., min_length=1, max_length=3)

    @classmethod
    def from_list(cls, data: list, city_count: int | None = None) -> CityRecommendationList:
        """Build from a raw list of dicts, optionally capping to *city_count*."""
        recommendations = [CityRecommendation(**item) for item in data]
        if city_count is not None:
            target = max(1, min(3, int(city_count)))
            recommendations = recommendations[:target]
        return cls(recommendations=recommendations)


class FinalRecommendation(_CityBase):
    """A city recommendation produced by the aggregator agent (no confidence score)."""
    pass


class FinalRecommendationList(BaseModel):
    """Wrapper around a list of aggregated final recommendations."""
    recommendations: list[FinalRecommendation] = Field(..., min_length=1, max_length=3)

    @classmethod
    def from_list(cls, data: list) -> FinalRecommendationList:
        """Build from a raw list of dicts."""
        return cls(recommendations=[FinalRecommendation(**item) for item in data])


class DayPlan(BaseModel):
    """A single day within a city itinerary."""
    day: int = Field(..., ge=1)
    title: str = Field(...)
    activities: list[str] = Field(..., min_length=1)


class Itinerary(BaseModel):
    """A complete day-by-day itinerary for one city."""
    days: list[DayPlan] = Field(..., min_length=1)

    @classmethod
    def from_list(cls, data: list) -> Itinerary:
        """Build from a raw list of day-plan dicts."""
        return cls(days=[DayPlan(**d) for d in data])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class TravelRequestBase(BaseModel):
    """Shared fields and validators for all travel-related request models.

    Centralizes budget, duration, and travel_styles validation so that
    PlanRequest, ChatRequest, and CompareRequest stay DRY.
    """
    budget: str = Field("mid")
    duration: int = Field(5, ge=1, le=30)
    travel_styles: list[str] = Field(default_factory=list)

    @field_validator("duration")
    @classmethod
    def valid_duration(cls, v: int) -> int:
        if not 1 <= v <= 30:
            raise ValueError("Duration must be between 1 and 30 days")
        return v

    @field_validator("budget")
    @classmethod
    def valid_budget(cls, v: str) -> str:
        return _validate_budget(v)

    @field_validator("travel_styles")
    @classmethod
    def valid_styles(cls, v: list[str]) -> list[str]:
        return _validate_travel_styles(v)


class PlanRequest(TravelRequestBase):
    """POST /plan — generate city recommendations and itineraries."""
    country: str = Field(..., min_length=1, max_length=100)
    city_count: int = Field(2, ge=1, le=3)
    session_id: str | None = Field(default=None)

    @field_validator("country")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)


class PlanResponse(BaseModel):
    """Response payload for POST /plan."""
    country: str
    budget: str
    duration: int
    city_count: int
    travel_styles: list[str]
    recommendations: list[dict]
    itineraries: list[dict]
    agent_details: dict
    session_id: str


class ChatRequest(TravelRequestBase):
    """POST /chat — ask a follow-up question about a planned trip."""
    country: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=500)
    recommendations: list[dict] = Field(default_factory=list)

    @field_validator("country")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)

    @field_validator("question")
    @classmethod
    def valid_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class ChatResponse(BaseModel):
    """Response payload for POST /chat."""
    answer: str


class CompareRequest(TravelRequestBase):
    """POST /compare — compare two countries side by side."""
    country_a: str = Field(..., min_length=1, max_length=100)
    country_b: str = Field(..., min_length=1, max_length=100)

    @field_validator("country_a", "country_b")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)
