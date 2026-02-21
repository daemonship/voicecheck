"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["STRIPE_SECRET_KEY"] = "test-key"
os.environ["STRIPE_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["SUPABASE_URL"] = "test-url"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["JWT_SECRET"] = "test-secret"


class MockSupabaseClient:
    """Mock Supabase client that handles multiple tables and operations."""
    
    def __init__(self):
        self.auth = Mock()
        self._tables = {}
        self._setup_auth()
    
    def _setup_auth(self):
        """Setup auth mock."""
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_user.email = "test@example.com"
        
        mock_session = Mock()
        mock_session.access_token = "test-token"
        
        self.auth.sign_up.return_value = Mock(user=mock_user, session=mock_session)
        self.auth.sign_in_with_password.return_value = Mock(user=mock_user, session=mock_session)
        self.auth.get_user.return_value = Mock(user=mock_user)
    
    def table(self, table_name):
        """Get or create a mock table."""
        if table_name not in self._tables:
            self._tables[table_name] = MockTable(table_name)
        return self._tables[table_name]


class MockTable:
    """Mock table that stores data and handles queries."""
    
    def __init__(self, name):
        self.name = name
        self._data = []
        self._query_filters = []
        self._current_query = {}
    
    def insert(self, data):
        """Insert data into the table."""
        from datetime import datetime
        
        if isinstance(data, dict):
            data = [data]
        
        result_data = []
        for item in data:
            # Create a copy to avoid modifying original
            item_copy = item.copy()
            if 'id' not in item_copy:
                item_copy['id'] = str(uuid.uuid4())
            if 'created_at' not in item_copy:
                item_copy['created_at'] = datetime.utcnow().isoformat()
            if 'updated_at' not in item_copy:
                item_copy['updated_at'] = datetime.utcnow().isoformat()
            self._data.append(item_copy)
            result_data.append(item_copy)
        
        mock_response = Mock()
        mock_response.data = result_data
        mock_response.execute = Mock(return_value=mock_response)
        return mock_response
    
    def select(self, *columns):
        """Start a select query."""
        self._current_query = {'operation': 'select', 'columns': columns}
        return self
    
    def eq(self, column, value):
        """Add equality filter."""
        self._query_filters.append(('eq', column, value))
        return self
    
    def is_(self, column, value):
        """Add IS filter (for NULL checks)."""
        self._query_filters.append(('is', column, value))
        return self
    
    def update(self, data):
        """Update data matching current filters."""
        self._current_query = {'operation': 'update', 'data': data}
        mock_response = Mock()
        mock_response.execute = Mock(return_value=mock_response)
        return mock_response
    
    def execute(self):
        """Execute the current query."""
        mock_response = Mock()
        
        if self._current_query.get('operation') == 'select':
            # Filter data based on query filters
            result = self._data.copy()
            for op, column, value in self._query_filters:
                if op == 'eq':
                    result = [item for item in result if item.get(column) == value]
                elif op == 'is':
                    if value is None:
                        result = [item for item in result if item.get(column) is None]
                    else:
                        result = [item for item in result if item.get(column) == value]
            mock_response.data = result
        else:
            mock_response.data = []
        
        # Clear filters for next query
        self._query_filters = []
        self._current_query = {}
        return mock_response


def create_mock_supabase_client():
    """Create a mock Supabase client."""
    return MockSupabaseClient()


@pytest.fixture(scope="session")
def mock_supabase():
    """Mock supabase client for entire test session."""
    mock_client = create_mock_supabase_client()
    with patch('supabase.create_client', return_value=mock_client):
        yield mock_client


@pytest.fixture(scope="session")
def mock_stripe():
    """Mock stripe for entire test session."""
    mock_session = Mock()
    mock_session.url = "https://checkout.stripe.com/test"
    with patch('stripe.checkout.Session.create', return_value=mock_session):
        with patch('stripe.Webhook.construct_event'):
            yield


@pytest.fixture(scope="session")
def app(mock_supabase, mock_stripe):
    """Create FastAPI app with mocked dependencies."""
    # Import app after mocking
    from backend.app.main import app
    return app


@pytest.fixture
async def client(app):
    """Async HTTP client for testing with auth header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, 
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"}
    ) as ac:
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
