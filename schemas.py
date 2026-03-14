from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


def _validate_country(v: str) -> str:
    v = v.strip()
    if len(v) < 2:
        raise ValueError("Country name must be at least 2 characters")
    if re.search(r"[<>{}\[\];]", v):
        raise ValueError("Country name contains invalid characters")
    if not re.search(r"[a-zA-Z]", v):
        raise ValueError("Country name must contain letters")
    return v


class CityRecommendation(BaseModel):
    city: str = Field(...)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(...)

    @field_validator("city", "reason")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class CityRecommendationList(BaseModel):
    recommendations: list[CityRecommendation] = Field(..., min_length=3, max_length=3)

    @classmethod
    def from_list(cls, data: list) -> CityRecommendationList:
        return cls(recommendations=[CityRecommendation(**item) for item in data])


class FinalRecommendation(BaseModel):
    city: str = Field(...)
    reason: str = Field(...)

    @field_validator("city", "reason")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class FinalRecommendationList(BaseModel):
    recommendations: list[FinalRecommendation] = Field(..., min_length=1, max_length=5)

    @classmethod
    def from_list(cls, data: list) -> FinalRecommendationList:
        return cls(recommendations=[FinalRecommendation(**item) for item in data])


class DayPlan(BaseModel):
    day: int = Field(..., ge=1)
    title: str = Field(...)
    activities: list[str] = Field(..., min_length=1)


class Itinerary(BaseModel):
    days: list[DayPlan] = Field(..., min_length=1)

    @classmethod
    def from_list(cls, data: list) -> Itinerary:
        return cls(days=[DayPlan(**d) for d in data])


class Budget(str, Enum):
    budget = "budget"
    mid = "mid"
    luxury = "luxury"


class TravelStyle(str, Enum):
    adventure = "adventure"
    relaxation = "relaxation"
    family = "family"
    honeymoon = "honeymoon"
    solo = "solo"
    culture = "culture"
    food = "food"
    nature = "nature"


class PlanRequest(BaseModel):
    country: str = Field(..., min_length=1, max_length=100)
    budget: str = Field("mid")
    duration: int = Field(5, ge=1, le=30)
    city_count: int = Field(2, ge=1, le=5)
    travel_styles: list[str] = Field(default_factory=list)
    session_id: str | None = Field(default=None)

    @field_validator("country")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)

    @field_validator("duration")
    @classmethod
    def valid_duration(cls, v: int) -> int:
        if not 1 <= v <= 30:
            raise ValueError("Duration must be between 1 and 30 days")
        return v

    @field_validator("budget")
    @classmethod
    def valid_budget(cls, v: str) -> str:
        v = v.strip().lower()
        try:
            return Budget(v).value
        except ValueError:
            raise ValueError(f"Budget must be one of: {', '.join(b.value for b in Budget)}")

    @field_validator("travel_styles")
    @classmethod
    def valid_styles(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip().lower() for s in v if s.strip()]
        invalid = [s for s in cleaned if s not in TravelStyle._value2member_map_]
        if invalid:
            raise ValueError(f"Invalid travel styles: {invalid}. Choose from: {', '.join(s.value for s in TravelStyle)}")
        return cleaned


class PlanResponse(BaseModel):
    country: str
    budget: str
    duration: int
    city_count: int
    travel_styles: list[str]
    recommendations: list[dict]
    itineraries: list[dict]
    agent_details: dict
    session_id: str


class ChatRequest(BaseModel):
    country: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=500)
    budget: str = Field("mid")
    duration: int = Field(5, ge=1, le=30)
    travel_styles: list[str] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)

    @field_validator("country")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)


class ChatResponse(BaseModel):
    answer: str


class CompareRequest(BaseModel):
    country_a: str = Field(..., min_length=1, max_length=100)
    country_b: str = Field(..., min_length=1, max_length=100)
    budget: str = Field("mid")
    duration: int = Field(5, ge=1, le=30)
    travel_styles: list[str] = Field(default_factory=list)

    @field_validator("country_a", "country_b")
    @classmethod
    def sanitize_country(cls, v: str) -> str:
        return _validate_country(v)
