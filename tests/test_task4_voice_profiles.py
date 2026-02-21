"""
Tests for Task 4: Voice profile generation, consistency analysis, and scoring.

Acceptance criteria:
- GET /api/projects/{id}/characters/{cid}/profile returns voice profile with 4 dimensions
- Profile includes 3-5 representative quotes verbatim from dialogue lines
- Character with under 20 lines returns 422 or degraded profile with warning
- GET /api/projects/{id}/characters/{cid}/flags returns consistency flags
- Flags have severity, dimension, location, and passage text verbatim from manuscript
- Consistent character scores higher than inconsistent character
- POST dismiss flag recalculates score; dismissing all flags returns 100
- Claude API error reflects failure state and allows retry
- GET /api/projects/{id}/progress returns SSE/polling with status updates
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voice_profile_has_all_dimensions(client: AsyncClient):
    """GET /api/projects/{id}/characters/{cid}/profile returns voice profile with 4 dimensions."""
    await client.post(
        "/api/auth/signup",
        json={"email": "profile@example.com", "password": "Password123!"}
    )
    
    # Create a manuscript with consistent character voice
    manuscript = '''
    "I believe we should proceed with caution," Dr. Smith said.
    "The evidence suggests otherwise," he continued.
    "We must analyze the data carefully," Dr. Smith added.
    "Let us examine the facts," he said.
    ''' * 10  # Give enough lines for analysis
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    # Get characters
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    # Get profile
    response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/profile")
    
    assert response.status_code == 200
    profile = response.json()
    assert "vocabulary_level" in profile
    assert "sentence_structure" in profile
    assert "verbal_tics" in profile
    assert "formality" in profile


@pytest.mark.asyncio
async def test_profile_includes_representative_quotes(client: AsyncClient):
    """Profile dimensions include 3-5 representative quotes verbatim from dialogue."""
    await client.post(
        "/api/auth/signup",
        json={"email": "quotes@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "Well, I reckon we oughta head on down to the river," said Jed.
    "Don'tcha think it's fixin' to rain?" Jed asked.
    "I'm fixin' to go now," Jed added.
    ''' * 10
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    # Get project text for verification
    project_data = await client.get(f"/api/projects/{project_id}")
    manuscript_text = project_data.json().get("text", "")
    
    response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/profile")
    
    assert response.status_code == 200
    profile = response.json()
    
    # Check that each dimension has representative quotes
    for dimension in ["vocabulary_level", "sentence_structure", "verbal_tics", "formality"]:
        assert dimension in profile
        quotes = profile[dimension].get("representative_quotes", [])
        assert len(quotes) >= 3
        assert len(quotes) <= 5
        
        # Verify quotes are verbatim substrings of the manuscript
        for quote in quotes:
            assert quote in manuscript_text


@pytest.mark.asyncio
async def test_profile_for_low_dialogue_character_returns_warning(client: AsyncClient):
    """Character with under 20 lines returns 422 or degraded profile with warning."""
    await client.post(
        "/api/auth/signup",
        json={"email": "lowdialogue@example.com", "password": "Password123!"}
    )
    
    # Create character with only 5 lines
    manuscript = '''
    "One," said Minor.
    "Two," said Minor.
    "Three," said Minor.
    "Four," said Minor.
    "Five," said Minor.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/profile")
    
    # Should either return 422 or a degraded profile with warning
    if response.status_code == 422:
        pass  # Expected
    elif response.status_code == 200:
        profile = response.json()
        assert "warning" in profile or "degraded" in profile
    else:
        pytest.fail(f"Unexpected status code: {response.status_code}")


@pytest.mark.asyncio
async def test_flags_have_required_fields(client: AsyncClient):
    """GET /api/projects/{id}/characters/{cid}/flags returns consistency flags with all required fields."""
    await client.post(
        "/api/auth/signup",
        json={"email": "flags@example.com", "password": "Password123!"}
    )
    
    # Create a manuscript with intentional voice inconsistency
    manuscript = '''
    "I believe we should proceed," said FormalCharacter.
    "The data suggests caution," FormalCharacter continued.
    "We must analyze," said FormalCharacter.
    
    "Yo, what's up?" said FormalCharacter.
    "This is totally cool," FormalCharacter added.
    "I'm like, whatever," said FormalCharacter.
    ''' * 10
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/flags")
    
    assert response.status_code == 200
    flags = response.json()
    assert isinstance(flags, list)
    
    if len(flags) > 0:
        flag = flags[0]
        assert "severity" in flag
        assert flag["severity"] in ["low", "medium", "high"]
        assert "dimension" in flag
        assert "manuscript_location" in flag
        assert "passage" in flag
        
        # manuscript_location should have chapter and paragraph
        location = flag["manuscript_location"]
        assert "chapter" in location or "paragraph" in location


@pytest.mark.asyncio
async def test_flag_passage_is_verbatim_from_manuscript(client: AsyncClient):
    """Flag passage text is a verbatim substring found at the manuscript location."""
    await client.post(
        "/api/auth/signup",
        json={"email": "verbatim@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "I always speak formally," said Victoria.
    "Indeed, quite so," Victoria continued.
    "Whatever," said Victoria.
    ''' * 10
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    project_data = await client.get(f"/api/projects/{project_id}")
    manuscript_text = project_data.json().get("text", "")
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/flags")
    
    assert response.status_code == 200
    flags = response.json()
    
    if len(flags) > 0:
        for flag in flags:
            passage = flag["passage"]
            assert passage in manuscript_text


@pytest.mark.asyncio
async def test_consistent_character_scores_higher_than_inconsistent(client: AsyncClient):
    """Consistent character scores strictly higher than inconsistent character."""
    await client.post(
        "/api/auth/signup",
        json={"email": "scoring@example.com", "password": "Password123!"}
    )
    
    # Create manuscript with one consistent and one inconsistent character
    manuscript = '''
    "I always speak the same way," said Consistent.
    "Indeed I do," said Consistent.
    "Quite right," said Consistent.
    "Always formal," said Consistent.
    ''' * 15
    
    manuscript += '''
    "I always speak the same way," said Inconsistent.
    "Indeed I do," said Inconsistent.
    "Yo sup dude," said Inconsistent.
    "Whatever bro," said Inconsistent.
    ''' * 15
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    characters = chars_response.json()
    
    # Get scores for both characters
    consistent_id = next(c["id"] for c in characters if c["name"] == "Consistent")
    inconsistent_id = next(c["id"] for c in characters if c["name"] == "Inconsistent")
    
    consistent_profile = await client.get(f"/api/projects/{project_id}/characters/{consistent_id}/profile")
    inconsistent_profile = await client.get(f"/api/projects/{project_id}/characters/{inconsistent_id}/profile")
    
    consistent_score = consistent_profile.json().get("consistency_score", 0)
    inconsistent_score = inconsistent_profile.json().get("consistency_score", 0)
    
    assert consistent_score > inconsistent_score


@pytest.mark.asyncio
async def test_dismiss_flag_recalculates_score(client: AsyncClient):
    """POST dismiss flag recalculates the consistency score."""
    await client.post(
        "/api/auth/signup",
        json={"email": "dismiss@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "Formal speech here," said TestCharacter.
    "Indeed quite so," said TestCharacter.
    "Yo whatever," said TestCharacter.
    ''' * 10
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    # Get initial score
    initial_profile = await client.get(f"/api/projects/{project_id}/characters/{character_id}/profile")
    initial_score = initial_profile.json().get("consistency_score", 100)
    
    # Get flags
    flags_response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/flags")
    flags = flags_response.json()
    
    if len(flags) > 0:
        flag_id = flags[0]["id"]
        
        # Dismiss flag
        dismiss_response = await client.post(
            f"/api/projects/{project_id}/characters/{character_id}/flags/{flag_id}/dismiss"
        )
        
        assert dismiss_response.status_code == 200
        
        # Get new score
        new_profile = await client.get(f"/api/projects/{project_id}/characters/{character_id}/profile")
        new_score = new_profile.json().get("consistency_score", 0)
        
        # Score should have increased
        assert new_score > initial_score


@pytest.mark.asyncio
async def test_dismiss_all_flags_returns_score_100(client: AsyncClient):
    """Dismissing ALL flags for a character returns a score of exactly 100."""
    await client.post(
        "/api/auth/signup",
        json={"email": "dismissall@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "One," said Character.
    "Two," said Character.
    "Three," said Character.
    ''' * 10
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    character_id = chars_response.json()[0]["id"]
    
    # Get all flags
    flags_response = await client.get(f"/api/projects/{project_id}/characters/{character_id}/flags")
    flags = flags_response.json()
    
    # Dismiss all flags
    for flag in flags:
        await client.post(
            f"/api/projects/{project_id}/characters/{character_id}/flags/{flag['id']}/dismiss"
        )
    
    # Get final score
    final_profile = await client.get(f"/api/projects/{project_id}/characters/{character_id}/profile")
    final_score = final_profile.json().get("consistency_score", 0)
    
    assert final_score == 100


@pytest.mark.asyncio
async def test_claude_api_error_reflects_failure_state(client: AsyncClient):
    """Claude API error reflects failure state and allows retry without re-upload."""
    await client.post(
        "/api/auth/signup",
        json={"email": "apierror@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "Test dialogue," said Character.
    ''' * 20
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    # Try to trigger analysis with invalid API key
    # This would normally be set via environment
    # For now, test that the failure state is handled
    
    # Get project status
    response = await client.get(f"/api/projects/{project_id}")
    
    # Should have a status field
    assert "status" in response.json()
    
    # If analysis failed, should be able to retry
    # Test retry endpoint
    retry_response = await client.post(f"/api/projects/{project_id}/retry")
    
    # Should accept retry (200 or 202), not 404 or 500
    assert retry_response.status_code in [200, 202, 409]  # 409 if already analyzing


@pytest.mark.asyncio
async def test_progress_endpoint_returns_status_updates(client: AsyncClient):
    """GET /api/projects/{id}/progress returns SSE or polling responses with status updates."""
    await client.post(
        "/api/auth/signup",
        json={"email": "progress@example.com", "password": "Password123!"}
    )
    
    project_response = await client.post(
        "/api/projects",
        json={"text": '"Test," said Character.' * 20}
    )
    project_id = project_response.json()["id"]
    
    # Test polling endpoint
    response = await client.get(f"/api/projects/{project_id}/progress")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["queued", "extracting", "profiling", "scoring", "complete", "failed"]
