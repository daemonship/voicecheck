"""Project endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
from typing import Optional

from ..services.auth import JWTBearer, AuthService
from ..services.project import ProjectService
from ..services.character import CharacterService
from ..services.stripe import StripeService
from ..models.project import ProjectCreate, Project

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _parse_project_input(request: Request):
    """
    Parse project input from either JSON body or multipart form.

    Returns (file_or_none, text_or_none).
    """
    content_type = request.headers.get("content-type", "")
    file = None
    text = None

    if "application/json" in content_type:
        body = await request.json()
        text = body.get("text")
    else:
        # Try form data (multipart/form-data or application/x-www-form-urlencoded)
        try:
            form = await request.form()
            text = form.get("text")
            file = form.get("file")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to parse request body")

    return file, text


@router.post("", status_code=201)
async def create_project(
    request: Request,
    current_user: dict = Depends(JWTBearer()),
):
    """Create a new project from .docx file or pasted text (form or JSON)."""
    file, text = await _parse_project_input(request)

    if not file and not text:
        raise HTTPException(status_code=400, detail="Either file or text must be provided")

    project_service = ProjectService()
    stripe_service = StripeService()

    try:
        if file and hasattr(file, 'filename'):
            # Validate file extension
            if not file.filename.lower().endswith('.docx'):
                raise HTTPException(status_code=422, detail="Only .docx files are supported")

            # Parse .docx
            parsed = await project_service.parse_docx(file)
            content_type = "docx"
            content_ref = file.filename
        elif text:
            # Parse pasted text
            parsed = await project_service.parse_text(text)
            content_type = "text"
            content_ref = "pasted"
        else:
            raise HTTPException(status_code=400, detail="Either file or text must be provided")

        # Check word count for paywall (15,000 words)
        if parsed["word_count"] > 15000:
            # TODO: check if user has active subscription
            checkout_url = await stripe_service.create_checkout_session(
                user_id=current_user["id"],
                email=current_user["email"]
            )
            return JSONResponse(
                status_code=402,
                content={"checkout_url": checkout_url}
            )

        # Create project in database
        project = await project_service.create_project(
            user_id=current_user["id"],
            title=parsed["title"],
            word_count=parsed["word_count"],
            chapter_count=parsed["chapter_count"],
            chapters=parsed["chapters"],
            content_type=content_type,
            content_ref=content_ref,
            full_text=parsed["full_text"],
            status="complete",
        )

        # Extract characters from the manuscript
        character_service = CharacterService()
        await character_service.create_characters_for_project(
            project_id=project.id,
            text=parsed["full_text"],
            chapters=parsed["chapters"]
        )

        return project.to_response()

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{project_id}/progress")
async def get_project_progress(
    project_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Get analysis progress for a project (polling endpoint)."""
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    return {
        "project_id": project_id,
        "status": project.status,
    }


@router.post("/{project_id}/retry")
async def retry_project_analysis(
    project_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Retry analysis for a project without re-uploading the manuscript."""
    project_service = ProjectService()
    project = await project_service.get_project(project_id, current_user["id"])

    if project.status == "extracting" or project.status == "profiling" or project.status == "scoring":
        return JSONResponse(
            status_code=409,
            content={"detail": "Analysis already in progress"}
        )

    # Reset status and re-trigger character extraction if needed
    # In production this would kick off an async job
    return {
        "project_id": project_id,
        "status": "queued",
        "message": "Analysis retry queued",
    }


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(JWTBearer()),
):
    """Retrieve a specific project."""
    project_service = ProjectService()

    try:
        project = await project_service.get_project(
            project_id=project_id,
            user_id=current_user["id"]
        )
        return project.to_response()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
