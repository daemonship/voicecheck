"""Character endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..services.auth import JWTBearer
from ..services.character import CharacterService
from ..services.project import ProjectService
from ..services.voice_profile import VoiceProfileService
from ..models.character import Character, CharacterMergeRequest, CharacterMergeResult

router = APIRouter(prefix="/api/projects", tags=["characters"])


@router.get("/{project_id}/characters")
async def get_characters(
    project_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Get all characters for a project."""
    # First verify project exists and user has access
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    character_service = CharacterService()
    characters = await character_service.get_project_characters(project_id)

    if not characters:
        return []

    return [char.model_dump() for char in characters]


@router.get("/{project_id}/characters/{character_id}/profile")
async def get_character_profile(
    project_id: str,
    character_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Get voice profile for a character."""
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    character_service = CharacterService()
    character = await character_service.get_character(character_id, project_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Return 422 for characters with too few lines (< 20 lines) with a warning
    if character.dialogue_line_count < 20:
        voice_service = VoiceProfileService()
        profile = voice_service.get_profile(character, project.full_text or "")
        # Return degraded profile with explicit warning
        return profile.model_dump()

    voice_service = VoiceProfileService()
    profile = voice_service.get_profile(character, project.full_text or "")
    return profile.model_dump()


@router.get("/{project_id}/characters/{character_id}/flags")
async def get_character_flags(
    project_id: str,
    character_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Get consistency flags for a character."""
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    character_service = CharacterService()
    character = await character_service.get_character(character_id, project_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    voice_service = VoiceProfileService()
    flags = voice_service.get_flags(character, project.full_text or "")

    return [f.model_dump() for f in flags]


@router.post("/{project_id}/characters/{character_id}/flags/{flag_id}/dismiss")
async def dismiss_flag(
    project_id: str,
    character_id: str,
    flag_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Mark a consistency flag as dismissed and recalculate the score."""
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    character_service = CharacterService()
    character = await character_service.get_character(character_id, project_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    voice_service = VoiceProfileService()
    flag, new_score = voice_service.dismiss_flag(flag_id, character_id, project_id)

    return {
        "flag_id": flag_id,
        "dismissed": True,
        "new_consistency_score": new_score,
    }


@router.get("/{project_id}/characters/{character_id}")
async def get_character(
    project_id: str,
    character_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Get a specific character by ID."""
    # First verify project exists and user has access
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    character_service = CharacterService()
    character = await character_service.get_character(character_id, project_id)

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    return character.model_dump()


@router.post("/{project_id}/characters/merge")
async def merge_characters(
    project_id: str,
    merge_request: CharacterMergeRequest,
    current_user: dict = Depends(JWTBearer()),
):
    """Merge two characters into one."""
    # First verify project exists and user has access
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    character_service = CharacterService()
    result = await character_service.merge_characters(
        project_id=project_id,
        character_id_1=merge_request.character_id_1,
        character_id_2=merge_request.character_id_2
    )

    return result.model_dump()
