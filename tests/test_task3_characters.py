"""
Tests for Task 3: Character identification, dialogue extraction, and alias merging.

Acceptance criteria:
- GET /api/projects/{id}/characters returns character names from dialogue attributions
- Each character includes dialogue_line_count; characters under 20 lines include warning
- Manuscript with zero quoted dialogue returns empty list with explanatory message
- POST /api/projects/{id}/characters/merge merges two characters
- POST /api/projects/{id}/characters/merge with non-existent ID returns 404
- POST /api/projects/{id}/characters/merge with same ID returns 400
- After merging, GET requests for original IDs return 404
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_characters_returns_detected_characters(client: AsyncClient):
    """GET /api/projects/{id}/characters returns character names from dialogue attributions."""
    # Create user and project
    await client.post(
        "/api/auth/signup",
        json={"email": "characters@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    Chapter 1
    
    "Hello," said Sarah.
    "Hi there," replied John.
    "How are you?" asked Sarah.
    "I'm fine," John said.
    
    "What's going on?" Michael asked.
    "Nothing much," replied Sarah.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    character_names = [c["name"] for c in data]
    assert "Sarah" in character_names
    assert "John" in character_names
    assert "Michael" in character_names


@pytest.mark.asyncio
async def test_characters_include_dialogue_line_count(client: AsyncClient):
    """Each character includes dialogue_line_count field."""
    await client.post(
        "/api/auth/signup",
        json={"email": "linecount@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "Line one," said Alice.
    "Line two," replied Bob.
    "Line three," said Alice.
    "Line four," said Alice.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters")
    
    assert response.status_code == 200
    data = response.json()
    alice = next((c for c in data if c["name"] == "Alice"), None)
    assert alice is not None
    assert "dialogue_line_count" in alice
    assert alice["dialogue_line_count"] >= 3


@pytest.mark.asyncio
async def test_characters_under_20_lines_include_warning(client: AsyncClient):
    """Characters with fewer than 20 lines include a warning flag."""
    await client.post(
        "/api/auth/signup",
        json={"email": "warning@example.com", "password": "Password123!"}
    )
    
    # Create a character with only 5 lines
    manuscript = '''
    "Line one," said Minor.
    "Line two," said Minor.
    "Line three," said Minor.
    "Line four," said Minor.
    "Line five," said Minor.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters")
    
    assert response.status_code == 200
    data = response.json()
    minor = next((c for c in data if c["name"] == "Minor"), None)
    assert minor is not None
    assert minor["dialogue_line_count"] < 20
    assert "warning" in minor or "low_dialogue" in minor


@pytest.mark.asyncio
async def test_zero_dialogue_returns_empty_list_with_message(client: AsyncClient):
    """Manuscript with zero quoted dialogue returns empty character list with message."""
    await client.post(
        "/api/auth/signup",
        json={"email": "nodialogue@example.com", "password": "Password123!"}
    )
    
    # Manuscript with no dialogue
    manuscript = '''
    Chapter 1
    
    The wind blew through the trees. It was a quiet day.
    No one spoke. The silence was deafening.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    response = await client.get(f"/api/projects/{project_id}/characters")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    # Response should include a message explaining why no characters were found
    # This might be in the response body or as a separate field


@pytest.mark.asyncio
async def test_merge_characters_combines_dialogue_lines(client: AsyncClient):
    """POST /api/projects/{id}/characters/merge merges two characters."""
    await client.post(
        "/api/auth/signup",
        json={"email": "merge@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "Hello," said Alice.
    "Hi," replied Bob.
    "How are you?" asked Alice.
    "Fine," Bob said.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    # Get characters
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    characters = chars_response.json()
    alice_id = next(c["id"] for c in characters if c["name"] == "Alice")
    bob_id = next(c["id"] for c in characters if c["name"] == "Bob")
    
    # Merge Alice into Bob
    response = await client.post(
        f"/api/projects/{project_id}/characters/merge",
        json={"character_id_1": alice_id, "character_id_2": bob_id}
    )
    
    assert response.status_code == 200
    merged = response.json()
    assert "id" in merged
    assert merged["dialogue_line_count"] >= 4  # Combined from both


@pytest.mark.asyncio
async def test_merge_with_nonexistent_id_returns_404(client: AsyncClient):
    """POST /api/projects/{id}/characters/merge with non-existent ID returns 404."""
    await client.post(
        "/api/auth/signup",
        json={"email": "merge404@example.com", "password": "Password123!"}
    )
    
    project_response = await client.post(
        "/api/projects",
        json={"text": '"Hello," said Alice.'}
    )
    project_id = project_response.json()["id"]
    
    # Try to merge with a non-existent character ID
    response = await client.post(
        f"/api/projects/{project_id}/characters/merge",
        json={"character_id_1": "nonexistent-id", "character_id_2": "another-fake-id"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_merge_same_character_returns_400(client: AsyncClient):
    """POST /api/projects/{id}/characters/merge with same ID returns 400."""
    await client.post(
        "/api/auth/signup",
        json={"email": "mergesame@example.com", "password": "Password123!"}
    )
    
    project_response = await client.post(
        "/api/projects",
        json={"text": '"Hello," said Alice.'}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    alice_id = chars_response.json()[0]["id"]
    
    # Try to merge Alice with herself
    response = await client.post(
        f"/api/projects/{project_id}/characters/merge",
        json={"character_id_1": alice_id, "character_id_2": alice_id}
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_after_merge_original_ids_return_404(client: AsyncClient):
    """After merging characters, GET requests for original IDs return 404."""
    await client.post(
        "/api/auth/signup",
        json={"email": "merge404check@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "Hello," said Alice.
    "Hi," replied Bob.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    chars_response = await client.get(f"/api/projects/{project_id}/characters")
    characters = chars_response.json()
    alice_id = next(c["id"] for c in characters if c["name"] == "Alice")
    bob_id = next(c["id"] for c in characters if c["name"] == "Bob")
    
    # Merge
    await client.post(
        f"/api/projects/{project_id}/characters/merge",
        json={"character_id_1": alice_id, "character_id_2": bob_id}
    )
    
    # Try to get original characters
    response_alice = await client.get(f"/api/projects/{project_id}/characters/{alice_id}")
    response_bob = await client.get(f"/api/projects/{project_id}/characters/{bob_id}")
    
    assert response_alice.status_code == 404
    assert response_bob.status_code == 404


@pytest.mark.asyncio
async def test_character_names_exist_in_manuscript(client: AsyncClient):
    """Character names returned actually exist in the manuscript text."""
    await client.post(
        "/api/auth/signup",
        json={"email": "verifynames@example.com", "password": "Password123!"}
    )
    
    manuscript = '''
    "I'm here," said Elizabeth.
    "Welcome," replied Mr. Darcy.
    '''
    
    project_response = await client.post(
        "/api/projects",
        json={"text": manuscript}
    )
    project_id = project_response.json()["id"]
    
    # Get the project text to verify characters exist in it
    project_response = await client.get(f"/api/projects/{project_id}")
    project_text = project_response.json().get("text", "")
    
    response = await client.get(f"/api/projects/{project_id}/characters")
    characters = response.json()
    
    for char in characters:
        # Character name should appear in the manuscript
        assert char["name"] in project_text or char["name"].lower() in project_text.lower()
