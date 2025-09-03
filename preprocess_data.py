#!/usr/bin/env python3
"""
Pre-process and cache data for fast app loading.
Run this script periodically to update the cached data files.
"""

import json
import logging
from datetime import datetime
from data_fetcher import fetch_all_swiss_gigs, process_gigs_data
from geo_processor import load_swiss_municipalities, match_gigs_to_municipalities
import geopandas as gpd
from shapely.geometry import shape

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def preprocess_all_data():
    """Fetch and pre-process all data, saving to JSON files for instant loading."""
    
    logger.info("Starting data preprocessing...")
    
    # 1. Fetch gigs from API
    logger.info("Fetching gigs from MX3 API...")
    raw_gigs = fetch_all_swiss_gigs()
    
    # 2. Process gigs data
    logger.info("Processing gigs data...")
    processed_gigs = process_gigs_data(raw_gigs)
    
    # 3. Load geography data
    logger.info("Loading Swiss municipalities...")
    geo_data = load_swiss_municipalities()
    
    # 4. Match gigs to municipalities  
    logger.info("Matching gigs to municipalities...")
    municipality_gigs = match_gigs_to_municipalities(processed_gigs)
    
    # 5. Create highly simplified geo data (only municipalities with gigs)
    logger.info("Creating simplified geo data for municipalities with gigs...")
    simplified_geo_features = []
    
    for municipality_name in municipality_gigs.keys():
        for feature in geo_data.get("features", []):
            props = feature.get("properties", {})
            feature_name = props.get("gemeinde.NAME") or props.get("NAME") or props.get("name")
            if feature_name == municipality_name:
                # Simplify geometry more aggressively for web performance
                geometry = feature.get("geometry")
                if geometry:
                    try:
                        # Convert to shapely geometry and simplify
                        geom = shape(geometry)
                        simplified_geom = geom.simplify(tolerance=0.007, preserve_topology=True)
                        
                        simplified_feature = {
                            "type": "Feature",
                            "properties": props,
                            "geometry": simplified_geom.__geo_interface__
                        }
                        simplified_geo_features.append(simplified_feature)
                    except Exception as e:
                        logger.warning(f"Could not simplify geometry for {municipality_name}: {e}")
                        simplified_geo_features.append(feature)
                break
    
    simplified_geo_data = {
        "type": "FeatureCollection",
        "features": simplified_geo_features
    }
    
    # 6. Save all data to JSON files
    logger.info("Saving processed data...")
    
    with open('data/processed_gigs.json', 'w') as f:
        json.dump(processed_gigs, f, indent=2, cls=DateTimeEncoder)
    
    with open('data/municipality_gigs.json', 'w') as f:
        json.dump(municipality_gigs, f, indent=2, cls=DateTimeEncoder)
    
    with open('data/simplified_geo.json', 'w') as f:
        json.dump(simplified_geo_data, f, indent=2)
    
    # 7. Save metadata
    metadata = {
        "last_updated": datetime.now().isoformat(),
        "total_gigs": len(processed_gigs),
        "municipalities_with_gigs": len(municipality_gigs),
        "total_municipalities": len(geo_data.get("features", [])),
        "geo_features_saved": len(simplified_geo_features)
    }
    
    with open('data/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Preprocessing complete!")
    logger.info(f"- {len(processed_gigs)} gigs across {len(municipality_gigs)} municipalities")
    logger.info(f"- Reduced geo features from 2175 to {len(simplified_geo_features)}")
    logger.info("Data saved to data/ directory for instant loading")

if __name__ == "__main__":
    preprocess_all_data()