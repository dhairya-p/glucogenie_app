from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel
from pydantic.config import ConfigDict


class PatientContext(BaseModel):
    """Shared patient context passed into all analytical agents.

    This is the cross-language source of truth for patient metadata.
    A matching Dart model should exist in `frontend/lib/models/patient_context.dart`.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: int
    sex: Optional[str] = None
    ethnicity: str
    height: Optional[int] = None  # Height in cm
    activity_level: Optional[str] = None
    location: Optional[str] = None
    conditions: List[str]
    medications: Optional[List[str]] = None

    model_config = ConfigDict(
        extra="ignore",
    )
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p).strip() or "there"


