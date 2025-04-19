import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock  # Add AsyncMock import
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MCPtastic.utils import utf8len, get_location_from_ip


def test_utf8len_ascii():
    """Test utf8len with ASCII characters."""
    assert utf8len("hello") == 5
    assert utf8len("") == 0
    assert utf8len("test123") == 7


def test_utf8len_unicode():
    """Test utf8len with Unicode characters."""
    # These emojis and special characters use multiple bytes in UTF-8
    assert utf8len("😀") == 4  # Single emoji
    assert utf8len("こんにちは") == 15  # Japanese characters
    assert utf8len("Café") == 5  # Latin character with accent


@pytest.mark.asyncio
@patch('httpx.AsyncClient')
async def test_get_location_from_ip_success(mock_client):
    """Test successful location lookup."""
    # Setup mock responses
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "lat": 37.7749,
        "lon": -122.4194,
        "city": "San Francisco",
        "country": "United States"
    }
    
    mock_elevation_response = MagicMock()
    mock_elevation_response.status_code = 200
    mock_elevation_response.json.return_value = {
        "results": [
            {"elevation": 100}
        ]
    }
    
    # Configure the mock client using AsyncMock for async methods
    mock_client_instance = AsyncMock()
    mock_client.return_value.__aenter__.return_value = mock_client_instance
    
    # The important fix: Set the awaited return values directly
    # Don't wrap responses in another AsyncMock
    mock_client_instance.get.side_effect = [
        mock_response,  # This will be the response for the first await
        mock_elevation_response  # This will be the response for the second await
    ]
    
    # Call the function
    result = await get_location_from_ip()
    
    # Verify results
    assert result["lat"] == 37.7749
    assert result["lon"] == -122.4194
    assert result["city"] == "San Francisco"
    assert result["country"] == "United States"
    assert result["altitude"] == 100


@pytest.mark.asyncio
@patch('httpx.AsyncClient')
async def test_get_location_from_ip_with_specified_ip(mock_client):
    """Test location lookup with a specified IP address."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "lat": 51.5074,
        "lon": -0.1278,
        "city": "London",
        "country": "United Kingdom"
    }
    
    mock_elevation_response = MagicMock()
    mock_elevation_response.status_code = 200
    mock_elevation_response.json.return_value = {
        "results": [
            {"elevation": 20}
        ]
    }