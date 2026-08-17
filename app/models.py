from datetime import date
from typing import Optional

from pydantic import BaseModel


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
    currentTopikLevel: str
    targetTopikLevel: str