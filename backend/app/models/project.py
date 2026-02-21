"""Project model."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectBase(BaseModel):
    title: str
    word_count: int
    chapter_count: int
    # We'll store chapters as JSON array of strings
    chapters: List[str]
    # Raw text or file path
    content_type: str  # "docx" or "text"
    content_ref: str  # path to file or raw text (truncated?)
    user_id: str
    full_text: Optional[str] = None  # Store full text for character extraction
    status: str = "complete"  # queued | extracting | profiling | scoring | complete | failed


class ProjectCreate(BaseModel):
    title: str
    word_count: int
    chapter_count: int
    chapters: List[str]
    content_type: str
    content_ref: str
    full_text: Optional[str] = None
    status: str = "complete"


class Project(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def to_response(self) -> dict:
        """Serialize for API responses, exposing full_text as 'text'."""
        d = self.model_dump()
        d["text"] = self.full_text
        return d
