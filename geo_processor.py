"""
GeoJSON processor for Swiss municipalities data
"""
import json
import logging
from typing import List, Dict, Set
import streamlit as st

from data_fetcher import normalize_municipality_name, find_municipality_match

logger = logging.getLogger(__name__)


@st.cache_data
def load_swiss_municipalities() -> Dict:
    """Load and process Swiss municipalities GeoJSON data"""
    logger.info("Loading Swiss municipalities GeoJSON...")
    
    # Try multiple potential paths for GeoJSON file
    possible_paths = [
        "data/gemeinden.geojson",
        "/Users/pmuww/swiss-bandmap/data/gemeinden.geojson",
        "data/simplified_geo.json"  # Fallback to existing processed data
    ]
    
    for path in possible_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                geo_data = json.load(f)
            
            logger.info(f"Loaded {len(geo_data['features'])} municipalities from {path}")
            return geo_data
            
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.error(f"Failed to load GeoJSON from {path}: {e}")
            continue
    
    logger.error("Could not load any GeoJSON data")
    st.error("Could not load Swiss municipalities data")
    return {"type": "FeatureCollection", "features": []}


@st.cache_data
def get_municipality_names() -> List[str]:
    """Extract all municipality names from GeoJSON"""
    geo_data = load_swiss_municipalities()
    
    municipality_names = []
    for feature in geo_data.get("features", []):
        props = feature.get("properties", {})
        name = props.get("gemeinde.NAME") or props.get("NAME") or props.get("name")
        if name:
            municipality_names.append(name)
    
    return sorted(municipality_names)


def simplify_geojson(geo_data: Dict, tolerance: float = 0.01) -> Dict:
    """
    Simplify GeoJSON geometries for better performance
    Note: This is a basic simplification. For production, consider using libraries like shapely
    """
    logger.info(f"Simplifying GeoJSON with tolerance {tolerance}")
    
    simplified = {
        "type": "FeatureCollection",
        "features": []
    }
    
    for feature in geo_data.get("features", []):
        # Keep the feature but potentially simplify geometry
        simplified_feature = {
            "type": "Feature",
            "properties": feature["properties"],
            "geometry": feature["geometry"]  # For now, keep original geometry
        }
        simplified["features"].append(simplified_feature)
    
    return simplified


def match_gigs_to_municipalities(gigs_data: List[Dict]) -> Dict:
    """
    Match gigs to municipalities using fuzzy matching
    Returns dict with municipality names as keys and gig lists as values
    """
    logger.info("Matching gigs to municipalities...")
    
    municipality_names = get_municipality_names()
    municipality_gigs = {}
    matched_count = 0
    unmatched_locations = set()
    
    for gig in gigs_data:
        location = gig.get("location", "")
        
        if not location:
            continue
            
        # Try to find municipality match in the location string
        matched_municipality = find_municipality_match(location, municipality_names)
        
        if matched_municipality:
            if matched_municipality not in municipality_gigs:
                municipality_gigs[matched_municipality] = []
            municipality_gigs[matched_municipality].append(gig)
            matched_count += 1
        else:
            unmatched_locations.add(location)
    
    logger.info(f"Matched {matched_count} gigs to municipalities")
    logger.info(f"Could not match {len(unmatched_locations)} unique locations")
    
    if unmatched_locations:
        logger.debug(f"Unmatched locations: {list(unmatched_locations)[:10]}")  # Show first 10
    
    return municipality_gigs


def create_municipality_lookup() -> Dict[str, Dict]:
    """Create a lookup dict for municipality properties by normalized name"""
    geo_data = load_swiss_municipalities()
    lookup = {}
    
    for feature in geo_data.get("features", []):
        props = feature.get("properties", {})
        name = props.get("gemeinde.NAME") or props.get("NAME")
        
        if name:
            normalized_name = normalize_municipality_name(name)
            lookup[normalized_name] = {
                "original_name": name,
                "canton_code": props.get("kanton.KUERZEL") or props.get("KANTON"),
                "canton_name": props.get("kanton.NAME") or props.get("KANTON_NAME"),
                "bfs_number": props.get("gemeinde.BFS_NUMMER") or props.get("BFS_NUMMER"),
                "geometry": feature.get("geometry")
            }
    
    return lookup