"""
Configuration settings for Swiss Bandmap application
"""
import os
from typing import List

# API Configuration
API_BASE_URL = "https://api.srgssr.ch/mx3/v2"
OAUTH_URL = "https://api.srgssr.ch/oauth/v1/accesstoken"

# Swiss Canton Codes
SWISS_CANTONS: List[str] = [
    "ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", 
    "SO", "BS", "BL", "SH", "AR", "AI", "SG", "GR", "AG", "TG", 
    "TI", "VD", "VS", "NE", "GE", "JU"
]

# App Configuration
APP_TITLE = "Swiss Live Music Map"
APP_DESCRIPTION = "Discover live music gigs across Swiss municipalities"
MAP_CENTER = [46.8182, 8.2275]  # Switzerland center
MAP_ZOOM = 8

# Data Configuration
CACHE_TTL = 3600  # 1 hour cache for data
MAX_GIGS_PER_REQUEST = 100