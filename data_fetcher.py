"""
Data fetcher for MX3 API to retrieve live music gigs across Swiss cantons
"""
import requests
import base64
import os
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import streamlit as st

from config import API_BASE_URL, OAUTH_URL, SWISS_CANTONS

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MX3APIClient:
    """Client for interacting with SRG SSR MX3 API"""
    
    def __init__(self):
        self.consumer_key = os.getenv("CONSUMER_KEY")
        self.consumer_secret = os.getenv("CONSUMER_SECRET")
        self.access_token = None
        self.token_expires_at = None
        
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("CONSUMER_KEY and CONSUMER_SECRET must be set in environment variables")
    
    def _get_access_token(self) -> str:
        """Get OAuth access token for API authentication"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
            
        # Create base64 encoded credentials
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Cache-Control": "no-cache",
            "Content-Length": "0"
        }
        
        try:
            response = requests.post(f"{OAUTH_URL}?grant_type=client_credentials", headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            
            # Calculate expiration time (expires_in is in seconds, token valid for 7 days)
            expires_in = token_data.get("expires_in", 604800)  # Default to 7 days if not specified
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)  # 1 hour buffer
            
            logger.info("Successfully obtained access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    def _make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated API request"""
        token = self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        url = f"{API_BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API request failed for {url}: {e}")
            return None
    
    def get_gigs_by_canton(self, canton_code: str) -> List[Dict]:
        """Get all gigs for a specific canton"""
        logger.info(f"Fetching gigs for canton: {canton_code}")
        
        data = self._make_api_request("gigs", {"state_code": canton_code})
        
        if data and data.get("response", {}).get("status") == "Ok":
            performances = data["response"].get("performances", [])
            logger.info(f"Found {len(performances)} gigs in {canton_code}")
            return performances
        else:
            logger.warning(f"No gigs found for canton {canton_code}")
            return []
    
    def get_band_details(self, band_id: int) -> Optional[Dict]:
        """Get detailed information about a specific band"""
        data = self._make_api_request(f"bands/{band_id}")
        
        if data and data.get("response", {}).get("status") == "Ok":
            return data["response"]["band"]
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_swiss_gigs() -> List[Dict]:
    """Fetch all current gigs across all Swiss cantons"""
    logger.info("Starting to fetch all Swiss gigs...")
    
    client = MX3APIClient()
    all_gigs = []
    
    # Progress bar for user feedback
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, canton in enumerate(SWISS_CANTONS):
        status_text.text(f"Fetching gigs for {canton}...")
        
        try:
            gigs = client.get_gigs_by_canton(canton)
            
            # Add canton info to each gig
            for gig in gigs:
                gig["canton"] = canton
                
            all_gigs.extend(gigs)
            
        except Exception as e:
            logger.error(f"Failed to fetch gigs for {canton}: {e}")
            st.warning(f"Could not load gigs for canton {canton}")
        
        # Update progress
        progress_bar.progress((i + 1) / len(SWISS_CANTONS))
    
    progress_bar.empty()
    status_text.empty()
    
    logger.info(f"Fetched total of {len(all_gigs)} gigs across Switzerland")
    return all_gigs


def normalize_municipality_name(name: str) -> str:
    """
    Normalize municipality name for matching:
    - Convert to lowercase
    - Remove whitespaces 
    - Remove special characters like dots, dashes, etc.
    """
    if not name:
        return ""
    
    # Convert to lowercase and remove special characters, keep only alphanumeric
    normalized = re.sub(r'[^a-zA-Z0-9\s]', '', name.lower())
    # Remove all whitespace
    normalized = re.sub(r'\s+', '', normalized)
    
    return normalized


def find_municipality_match(location_text: str, municipality_names: List[str]) -> Optional[str]:
    """
    Find municipality match in location text (e.g., 'zürich roxy bar' should match 'Zürich')
    Returns the original municipality name from the GeoJSON data if found
    """
    if not location_text or not municipality_names:
        return None
    
    # Normalize the location text for comparison
    normalized_location = normalize_municipality_name(location_text)
    
    # Try to find municipality names within the location text
    best_match = None
    longest_match_length = 0
    
    for municipality in municipality_names:
        normalized_municipality = normalize_municipality_name(municipality)
        
        if normalized_municipality and normalized_municipality in normalized_location:
            # Prefer longer matches (e.g., "sanktgallen" over "gallen")
            if len(normalized_municipality) > longest_match_length:
                longest_match_length = len(normalized_municipality)
                best_match = municipality
    
    return best_match


def process_gigs_data(raw_gigs: List[Dict]) -> List[Dict]:
    """Process and normalize gigs data for display"""
    processed_gigs = []
    
    for gig in raw_gigs:
        try:
            # Extract key information
            location = gig.get("location", "")
            processed_gig = {
                "date": gig.get("date"),
                "band_name": gig.get("band_name"),
                "band_id": gig.get("band", {}).get("id"),
                "venue": gig.get("stage_name"),
                "location": location,
                "location_normalized": normalize_municipality_name(location),
                "canton": gig.get("canton"),
                "band_image_thumb": gig.get("band", {}).get("url_for_image_thumb"),
                "band_categories": [cat.get("name") for cat in gig.get("band", {}).get("categories", [])],
                "mx3_url": f"https://mx3.ch/bands/{gig.get('band', {}).get('id')}" if gig.get("band", {}).get("id") else None,
                "event_name": gig.get("name"),
                "venue_url": gig.get("location_url")
            }
            
            # Parse date
            if processed_gig["date"]:
                try:
                    processed_gig["parsed_date"] = datetime.fromisoformat(processed_gig["date"].replace("Z", "+00:00"))
                except:
                    processed_gig["parsed_date"] = None
            else:
                processed_gig["parsed_date"] = None
            
            processed_gigs.append(processed_gig)
            
        except Exception as e:
            logger.warning(f"Failed to process gig: {e}")
    
    # Sort by date (oldest first), then by band name alphabetically
    processed_gigs.sort(
        key=lambda x: (
            x["parsed_date"] or datetime.min,
            x["band_name"] or ""
        ),
        reverse=False  # oldest first
    )
    
    return processed_gigs