"""
Simplified unit tests for app module (avoiding streamlit session state complexity)
"""
import pytest
from unittest.mock import Mock, patch, mock_open
import json
from datetime import datetime, timedelta

from app import (
    is_data_stale,
    create_gig_tooltip,
    create_gig_popup,
    create_gigs_table
)


class TestDataStaleness:
    """Test data staleness detection"""
    
    def test_is_data_stale_fresh_data(self):
        """Test with fresh data (less than 24 hours old)"""
        fresh_timestamp = datetime.now() - timedelta(hours=12)
        metadata = {
            "last_updated": fresh_timestamp.isoformat()
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(metadata))):
            assert is_data_stale() == False
    
    def test_is_data_stale_old_data(self):
        """Test with stale data (more than 24 hours old)"""
        old_timestamp = datetime.now() - timedelta(hours=30)
        metadata = {
            "last_updated": old_timestamp.isoformat()
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(metadata))):
            assert is_data_stale() == True
    
    def test_is_data_stale_missing_file(self):
        """Test when metadata file is missing"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            assert is_data_stale() == True


class TestUIComponents:
    """Test UI component generation"""
    
    def test_create_gig_tooltip_no_gigs(self):
        """Test tooltip creation with no gigs"""
        tooltip = create_gig_tooltip([], "Zürich")
        assert "Zürich" in tooltip
        assert "No upcoming gigs" in tooltip
    
    def test_create_gig_popup_with_gigs(self):
        """Test popup creation with gigs"""
        gigs = [
            {
                "band_name": "Test Band",
                "band": {"id": 123},
                "venue": "Test Venue", 
                "parsed_date": datetime(2024, 12, 25, 20, 0)
            }
        ]
        popup = create_gig_popup(gigs, "Zürich")
        
        assert "Zürich" in popup
        assert "Test Band" in popup
        assert "Test Venue" in popup
        assert "mx3.ch/123" in popup
    
    def test_create_gigs_table_with_data(self):
        """Test table creation with gig data"""
        gigs = [
            {
                "band_name": "Test Band",
                "band": {"id": 123},
                "venue": "Test Venue",
                "location": "Zürich",
                "canton": "ZH",
                "band_categories": ["Rock", "Pop"],
                "parsed_date": datetime(2024, 12, 25, 20, 0)
            }
        ]
        
        df = create_gigs_table(gigs)
        
        assert len(df) == 1
        assert "Test Band" in df.iloc[0]["Band"]