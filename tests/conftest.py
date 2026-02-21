"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["STRIPE_SECRET_KEY"] = "test-key"
os.environ["STRIPE_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["SUPABASE_URL"] = "test-url"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["JWT_SECRET"] = "test-secret"


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    from backend.app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_docx_path():
    """Path to a sample .docx file for testing."""
    return Path("/tmp/test_manuscript.docx")


@pytest.fixture
def sample_manuscript_text():
    """Sample manuscript text for testing."""
    return """
Chapter 1

"I can't believe you're here," Sarah said, her hands trembling.

John smiled. "I wouldn't miss this for the world."

"But what about the danger?" asked Michael, stepping forward.

"Danger is my business," John replied with a wink.

Chapter 2

The morning sun cast long shadows across the room. Sarah paced nervously.

"You worry too much," John said, leaning against the wall.

"Someone has to worry!" Sarah exclaimed.

Michael nodded. "She's right, you know. We need a plan."

John laughed. "Where's your sense of adventure?"

Chapter 3

"I have a bad feeling about this," Sarah whispered.

"Don't be silly," John replied. "Everything will be fine."

Michael checked his watch. "We should go. Now."

"Agreed," John said. "Let's move."

Sarah took a deep breath. "Okay. I'm ready."
"""
