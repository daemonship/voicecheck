"""Voice profile and consistency flag models."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class VoiceDimension(BaseModel):
    """A single voice dimension with description and representative quotes."""

    description: str
    representative_quotes: List[str]


class ManuscriptLocation(BaseModel):
    """Location within a manuscript."""

    chapter: int
    paragraph: int


class VoiceProfile(BaseModel):
    """Full voice profile for a character."""

    character_id: str
    project_id: str
    vocabulary_level: VoiceDimension
    sentence_structure: VoiceDimension
    verbal_tics: VoiceDimension
    formality: VoiceDimension
    consistency_score: float
    warning: Optional[str] = None


class ConsistencyFlag(BaseModel):
    """A consistency flag marking a voice deviation."""

    id: str
    character_id: str
    project_id: str
    severity: Literal["low", "medium", "high"]
    dimension: str
    manuscript_location: ManuscriptLocation
    passage: str
    dismissed: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
