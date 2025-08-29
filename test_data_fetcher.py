"""
Unit tests for data_fetcher module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from data_fetcher import (
    MX3APIClient,
    normalize_municipality_name,
    find_municipality_match,
    process_gigs_data
)


class TestMX3APIClient:
    """Test the MX3 API client"""
    
    def test_init_missing_credentials(self):
        """Test client initialization without credentials"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="CONSUMER_KEY and CONSUMER_SECRET must be set"):
                MX3APIClient()
    
    @patch.dict('os.environ', {'CONSUMER_KEY': 'test_key', 'CONSUMER_SECRET': 'test_secret'})
    def test_init_success(self):
        """Test successful client initialization"""
        client = MX3APIClient()
        assert client.consumer_key == 'test_key'
        assert client.consumer_secret == 'test_secret'
        assert client.access_token is None
    
    @patch.dict('os.environ', {'CONSUMER_KEY': 'test_key', 'CONSUMER_SECRET': 'test_secret'})
    @patch('requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful token retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        client = MX3APIClient()
        token = client._get_access_token()
        
        assert token == "test_token"
        assert client.access_token == "test_token"
        mock_post.assert_called_once()
    
    @patch.dict('os.environ', {'CONSUMER_KEY': 'test_key', 'CONSUMER_SECRET': 'test_secret'})
    @patch('requests.get')
    def test_get_gigs_by_canton_success(self, mock_get):
        """Test successful gigs retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": {
                "status": "Ok",
                "performances": [
                    {"band_name": "Test Band", "location": "Zurich"},
                    {"band_name": "Another Band", "location": "Basel"}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        with patch.object(MX3APIClient, '_get_access_token', return_value='test_token'):
            client = MX3APIClient()
            gigs = client.get_gigs_by_canton('ZH')
        
        assert len(gigs) == 2
        assert gigs[0]["band_name"] == "Test Band"


class TestMunicipalityNameProcessing:
    """Test municipality name normalization and matching"""
    
    def test_normalize_municipality_name(self):
        """Test municipality name normalization"""
        assert normalize_municipality_name("Zürich") == "zrich"  # ü gets removed
        assert normalize_municipality_name("Sankt Gallen") == "sanktgallen"
        assert normalize_municipality_name("Bern-Stadt") == "bernstadt"
        assert normalize_municipality_name("") == ""
        assert normalize_municipality_name(None) == ""
    
    def test_find_municipality_match(self):
        """Test municipality matching logic"""
        municipalities = ["Zürich", "Basel", "Bern", "Sankt Gallen"]
        
        # Exact matches (considering ü removal)
        assert find_municipality_match("zrich venue", municipalities) == "Zürich"
        assert find_municipality_match("Basel Concert Hall", municipalities) == "Basel"
        
        # Partial matches
        assert find_municipality_match("sankt gallen venue", municipalities) == "Sankt Gallen"
        
        # No match
        assert find_municipality_match("Geneva", municipalities) is None
        assert find_municipality_match("", municipalities) is None
        
        # Prefer longer matches
        municipalities_with_overlap = ["Gallen", "Sankt Gallen"] 
        assert find_municipality_match("sankt gallen venue", municipalities_with_overlap) == "Sankt Gallen"


class TestProcessGigsData:
    """Test gig data processing"""
    
    def test_process_gigs_data_basic(self):
        """Test basic gig data processing"""
        raw_gigs = [
            {
                "date": "2024-12-25T20:00:00Z",
                "band_name": "Test Band",
                "band": {"id": 123},
                "stage_name": "Test Venue",
                "location": "Zurich",
                "canton": "ZH"
            }
        ]
        
        processed = process_gigs_data(raw_gigs)
        
        assert len(processed) == 1
        gig = processed[0]
        assert gig["band_name"] == "Test Band"
        assert gig["band_id"] == 123
        assert gig["venue"] == "Test Venue"
        assert gig["location"] == "Zurich"
        assert gig["canton"] == "ZH"
        assert isinstance(gig["parsed_date"], datetime)
    
    def test_process_gigs_data_invalid_date(self):
        """Test processing with invalid date"""
        raw_gigs = [
            {
                "date": "invalid-date",
                "band_name": "Test Band",
                "location": "Zurich"
            }
        ]
        
        processed = process_gigs_data(raw_gigs)
        
        assert len(processed) == 1
        assert processed[0]["parsed_date"] is None
    
    def test_process_gigs_data_sorting(self):
        """Test that gigs are sorted by date then band name"""
        raw_gigs = [
            {
                "date": "2024-12-26T20:00:00Z",
                "band_name": "Z Band",
                "location": "Zurich"
            },
            {
                "date": "2024-12-25T20:00:00Z", 
                "band_name": "A Band",
                "location": "Basel"
            },
            {
                "date": "2024-12-25T20:00:00Z",
                "band_name": "B Band", 
                "location": "Bern"
            }
        ]
        
        processed = process_gigs_data(raw_gigs)
        
        assert len(processed) == 3
        # Should be sorted by date first (25th before 26th), then alphabetically
        assert processed[0]["band_name"] == "A Band"
        assert processed[1]["band_name"] == "B Band" 
        assert processed[2]["band_name"] == "Z Band"