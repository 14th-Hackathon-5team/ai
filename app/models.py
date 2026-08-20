from datetime import date
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class RecommendationType(StrEnum):
    LAW = "LAW"
    UNIVERSITY = "UNIVERSITY"


class RecommendationPriority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NotificationCategory(StrEnum):
    VISA = "VISA"
    LEGAL = "LEGAL"
    TOPIK = "TOPIK"
    ADMISSION = "ADMISSION"
    SCHOOL = "SCHOOL"
    LIFE = "LIFE"
    PART_TIME = "PART_TIME"
    HOUSING = "HOUSING"
    ENTRY = "ENTRY"
    SUPPORT = "SUPPORT"


class UserProfile(BaseModel):
    userId: int
    nationality: str
    birthYear: int
    userStatus: str
    schoolName: Optional[str] = None
    entryDate: date
    visaType: str
    hasAlienRegistration: bool
    stayExpirationDate: Optional[date] = None
    housingType: Optional[str] = None
    isParentSupported: Optional[bool] = None
    partTimeStatus: Optional[str] = None
    partTimeStartDate: Optional[date] = None
    hasPartTimePermit: Optional[bool] = None
    currentTopikLevel: str
    targetTopikLevel: str
    language: str


class RecommendationTrigger(BaseModel):
    type: str
    daysRemaining: Optional[int] = None


class RecommendationRequest(BaseModel):
    user: UserProfile
    trigger: RecommendationTrigger


class RecommendationDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    category: NotificationCategory


class RecommendationItem(BaseModel):
    type: RecommendationType
    priority: RecommendationPriority
    title: str
    reason: str
    detail: RecommendationDetail


class RecommendationResponse(BaseModel):
    userId: int
    summary: str
    recommendations: list[RecommendationItem]