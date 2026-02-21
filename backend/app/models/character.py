"""Character model."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class DialogueLine(BaseModel):
    """A single line of dialogue spoken by a character."""
    text: str
    chapter_index: int
    paragraph_index: int


class CharacterBase(BaseModel):
    """Base character model."""
    name: str
    project_id: str
    dialogue_lines: List[DialogueLine]
    dialogue_line_count: int
    warning: Optional[str] = None


class CharacterCreate(BaseModel):
    """Character creation model."""
    name: str
    project_id: str
    dialogue_lines: List[DialogueLine]


class Character(CharacterBase):
    """Full character model with ID and timestamps."""
    id: str
    created_at: datetime
    updated_at: datetime
    merged_into_id: Optional[str] = None

    class Config:
        from_attributes = True


class CharacterMergeRequest(BaseModel):
    """Request to merge two characters."""
    character_id_1: str
    character_id_2: str


class CharacterMergeResult(BaseModel):
    """Result of a character merge operation."""
    id: str
    name: str
    dialogue_line_count: int
    dialogue_lines: List[DialogueLine]
    merged_character_ids: List[str]
