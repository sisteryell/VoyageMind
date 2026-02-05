"""
Simplified schemas - all in one file.
"""
from pydantic import BaseModel, Field, field_validator


# City Recommendation Schema
class CityRecommendation(BaseModel):
    """Single city recommendation."""
    city: str = Field(..., description="City name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0-1")
    reason: str = Field(..., description="Brief explanation")
    
    @field_validator('city', 'reason')
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class CityRecommendationList(BaseModel):
    """List of 3 city recommendations."""
    recommendations: list[CityRecommendation] = Field(..., min_length=3, max_length=3)
    
    @classmethod
    def from_list(cls, data: list) -> 'CityRecommendationList':
        return cls(recommendations=[CityRecommendation(**item) for item in data])


# Final Recommendation Schema
class FinalRecommendation(BaseModel):
    """Final city recommendation."""
    city: str = Field(..., description="City name")
    reason: str = Field(..., description="Final justification")
    
    @field_validator('city', 'reason')
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class FinalRecommendationList(BaseModel):
    """List of 2 final recommendations."""
    recommendations: list[FinalRecommendation] = Field(..., min_length=2, max_length=2)
    
    @classmethod
    def from_list(cls, data: list) -> 'FinalRecommendationList':
        return cls(recommendations=[FinalRecommendation(**item) for item in data])
