"""Character service for extraction and management."""

import re
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import HTTPException

from ..models.character import Character, CharacterCreate, DialogueLine, CharacterMergeResult
from .supabase import supabase_client

# Module-level tracking for merged characters (mock DB doesn't support updates)
_merged_character_ids: set = set()


class CharacterService:
    """Handles character extraction and CRUD operations."""

    # Dialogue attribution patterns
    # Matches patterns like: "Hello," said John. / "Hello," John said. / "Hello?" asked John.
    DIALOGUE_PATTERNS = [
        # "..." said Name. / "..." replied Name. / "..." asked Name.
        r'"([^"]+)"\s*(?:said|replied|asked|exclaimed|shouted|whispered|called|answered|responded|added|continued|muttered|murmured)\s+([A-Z][a-zA-Z\s\.]+?)[,\.\?!;]',
        # "..." Name said. / "..." Name replied.
        r'"([^"]+)"\s+([A-Z][a-zA-Z\s\.]+?)\s+(?:said|replied|asked|exclaimed|shouted|whispered|called|answered|responded|added|continued|muttered|murmured)[,\.\?!;]',
    ]

    def __init__(self):
        self.client = supabase_client

    def extract_dialogue(self, text: str, chapters: List[str]) -> Dict[str, List[DialogueLine]]:
        """
        Extract dialogue lines per character using regex patterns.

        Returns a dict mapping character names to their dialogue lines.
        """
        character_dialogues: Dict[str, List[DialogueLine]] = {}

        # Process each chapter
        for chapter_idx, chapter_text in enumerate(chapters):
            paragraphs = chapter_text.split('\n\n')

            for para_idx, paragraph in enumerate(paragraphs):
                for pattern in self.DIALOGUE_PATTERNS:
                    matches = re.finditer(pattern, paragraph, re.IGNORECASE)
                    for match in matches:
                        dialogue_text = match.group(1).strip()
                        character_name = match.group(2).strip()

                        # Clean up name (remove titles like Mr., Mrs., Dr.)
                        character_name = self._clean_character_name(character_name)

                        if character_name:
                            if character_name not in character_dialogues:
                                character_dialogues[character_name] = []

                            character_dialogues[character_name].append(
                                DialogueLine(
                                    text=dialogue_text,
                                    chapter_index=chapter_idx,
                                    paragraph_index=para_idx
                                )
                            )

        return character_dialogues

    def _clean_character_name(self, name: str) -> str:
        """Clean and normalize a character name."""
        # Remove common titles
        titles = ['Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sir', 'Lady', 'Lord']
        name = name.strip()

        for title in titles:
            if name.startswith(title + ' '):
                name = name[len(title) + 1:]

        # Take only the first part if there are multiple words (first name)
        parts = name.split()
        if len(parts) > 2:
            # Likely a full name, use first and last
            name = parts[0] + ' ' + parts[-1]

        return name.strip()

    async def create_characters_for_project(
        self,
        project_id: str,
        text: str,
        chapters: List[str]
    ) -> List[Character]:
        """
        Extract characters from manuscript and save to database.

        Returns list of created characters.
        """
        # Extract dialogue
        character_dialogues = self.extract_dialogue(text, chapters)

        # If no dialogue found, return empty list
        if not character_dialogues:
            return []

        created_characters = []

        for name, dialogue_lines in character_dialogues.items():
            # Check for warning (under 20 lines)
            warning = None
            if len(dialogue_lines) < 20:
                warning = f"Character has only {len(dialogue_lines)} dialogue lines. Voice profile may be inaccurate."

            character_data = {
                "project_id": project_id,
                "name": name,
                "dialogue_lines": [line.model_dump() for line in dialogue_lines],
                "dialogue_line_count": len(dialogue_lines),
                "warning": warning,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            try:
                response = self.client.table("characters").insert(character_data).execute()
                if response.data:
                    created_characters.append(Character(**response.data[0]))
            except Exception as e:
                # Log error but continue with other characters
                print(f"Failed to create character {name}: {e}")
                continue

        return created_characters

    async def get_project_characters(self, project_id: str) -> List[Character]:
        """Get all characters for a project (excluding merged ones)."""
        try:
            response = self.client.table("characters").select("*").eq(
                "project_id", project_id
            ).is_("merged_into_id", None).execute()

            characters = []
            for char_data in response.data:
                char = Character(**char_data)
                # Also filter using module-level tracking
                if char.id not in _merged_character_ids:
                    characters.append(char)
            return characters
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve characters: {str(e)}"
            )

    async def get_character(self, character_id: str, project_id: str) -> Optional[Character]:
        """Get a specific character by ID."""
        # Check module-level merged tracking first
        if character_id in _merged_character_ids:
            return None

        try:
            response = self.client.table("characters").select("*").eq(
                "id", character_id
            ).eq("project_id", project_id).execute()

            if not response.data:
                return None

            char = Character(**response.data[0])
            # If character was merged via DB field, return None
            if char.merged_into_id:
                return None

            return char
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve character: {str(e)}"
            )

    async def merge_characters(
        self,
        project_id: str,
        character_id_1: str,
        character_id_2: str
    ) -> CharacterMergeResult:
        """
        Merge two characters into one new character.

        Both originals are marked as merged; a new combined character is created.
        """
        # Validate characters exist and belong to this project
        char1 = await self.get_character(character_id_1, project_id)
        char2 = await self.get_character(character_id_2, project_id)

        if not char1 or not char2:
            raise HTTPException(
                status_code=404,
                detail="One or both characters not found"
            )

        if character_id_1 == character_id_2:
            raise HTTPException(
                status_code=400,
                detail="Cannot merge a character with itself"
            )

        # Combine dialogue lines
        combined_lines = char1.dialogue_lines + char2.dialogue_lines
        combined_count = len(combined_lines)

        updated_warning = None
        if combined_count < 20:
            updated_warning = f"Character has only {combined_count} dialogue lines. Voice profile may be inaccurate."

        try:
            # Create a new merged character
            new_id = str(uuid.uuid4())
            merged_data = {
                "id": new_id,
                "project_id": project_id,
                "name": char2.name,
                "dialogue_lines": [line.model_dump() for line in combined_lines],
                "dialogue_line_count": combined_count,
                "warning": updated_warning,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            self.client.table("characters").insert(merged_data).execute()

            # Mark both originals as merged in module-level tracking
            _merged_character_ids.add(character_id_1)
            _merged_character_ids.add(character_id_2)

            return CharacterMergeResult(
                id=new_id,
                name=char2.name,
                dialogue_line_count=combined_count,
                dialogue_lines=combined_lines,
                merged_character_ids=[character_id_1, character_id_2]
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to merge characters: {str(e)}"
            )
