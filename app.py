"""
Swiss Bandmap - Interactive Music Gig Visualization
Streamlit app showing live music gigs across Swiss municipalities
"""
import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import logging

from config import APP_TITLE, APP_DESCRIPTION, MAP_CENTER, MAP_ZOOM
from data_fetcher import fetch_all_swiss_gigs, process_gigs_data
from geo_processor import (
    load_swiss_municipalities, 
    match_gigs_to_municipalities,
    create_municipality_lookup,
    simplify_geojson
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

def create_gig_tooltip(gigs: list) -> str:
    """Create simple HTML tooltip for quick municipality info"""
    if not gigs:
        return "No upcoming gigs"
    
    return f"<b>{len(gigs)} upcoming gig{'s' if len(gigs) > 1 else ''}</b><br>Click for details"

def create_gig_popup(gigs: list, municipality_name: str) -> str:
    """Create detailed HTML popup with clickable band links"""
    if not gigs:
        return f"<h3>{municipality_name}</h3>No upcoming gigs"
    
    html = f"<h3>{municipality_name}</h3>"
    html += f"<p><b>{len(gigs)} upcoming gig{'s' if len(gigs) > 1 else ''}</b></p>"
    html += "<div style='max-height: 400px; overflow-y: auto; width: 350px;'>"
    
    # Sort gigs by date (oldest first as requested)
    sorted_gigs = sorted(gigs, key=lambda x: x.get("parsed_date") or "", reverse=False)
    
    for gig in sorted_gigs:
        band_name = gig.get("band_name", "Unknown Band")
        band_id = gig.get("band", {}).get("id") if isinstance(gig.get("band"), dict) else gig.get("band_id")
        venue = gig.get("venue", "")
        date_str = ""
        
        if gig.get("parsed_date"):
            parsed_date = gig["parsed_date"]
            if isinstance(parsed_date, str):
                try:
                    parsed_date = datetime.fromisoformat(parsed_date.replace('Z', '+00:00'))
                    date_str = parsed_date.strftime("%d.%m.%Y")
                except:
                    date_str = gig.get("date", "")
            else:
                date_str = parsed_date.strftime("%d.%m.%Y")
        
        html += f"<div style='margin-bottom: 12px; padding: 8px; background-color: #f9f9f9; border-radius: 4px;'>"
        
        # Clickable band name with correct mx3 URL format
        if band_id:
            html += f"<b><a href='https://mx3.ch/{band_id}' target='_blank' style='color: #0066cc; text-decoration: none;'>{band_name}</a></b><br>"
        else:
            html += f"<b>{band_name}</b><br>"
        
        if venue:
            html += f"📍 {venue}<br>"
        if date_str:
            html += f"📅 {date_str}<br>"
        html += f"</div>"
    
    html += "</div>"
    return html


def create_interactive_map(municipality_gigs: dict, geo_data: dict) -> folium.Map:
    """Create interactive folium map with gig data"""
    logger.info("Creating interactive map...")
    
    # Create base map
    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="OpenStreetMap"
    )
    
    # Calculate gig counts for heatmap coloring
    max_gigs = max([len(gigs) for gigs in municipality_gigs.values()]) if municipality_gigs else 1
    
    # Add only municipalities with gigs to map (for performance)
    for municipality_name, gigs in municipality_gigs.items():
        # Find the corresponding feature in geo_data
        municipality_feature = None
        for feature in geo_data.get("features", []):
            props = feature.get("properties", {})
            feature_name = props.get("gemeinde.NAME") or props.get("NAME") or props.get("name")
            if feature_name == municipality_name:
                municipality_feature = feature
                break
        
        if not municipality_feature:
            continue
            
        # Clean up properties for folium - ensure no dots in keys
        props = municipality_feature.get("properties", {})
        clean_props = {}
        for key, value in props.items():
            clean_key = key.replace(".", "_")
            clean_props[clean_key] = value
        
        # Create a clean feature for folium
        clean_feature = {
            "type": "Feature",
            "properties": clean_props,
            "geometry": municipality_feature.get("geometry")
        }
            
        gig_count = len(gigs)
        
        # Color intensity based on gig count
        intensity = min(gig_count / max_gigs, 1.0)
        red = int(255 * intensity)
        color = f"#{red:02x}3333"
        fill_color = f"#{red:02x}4444"
        fill_opacity = 0.8
        
        # Create tooltip and popup
        tooltip_html = create_gig_tooltip(gigs)
        popup_html = create_gig_popup(gigs, municipality_name)
        
        # Add municipality to map
        folium.GeoJson(
            clean_feature,
            style_function=lambda x, color=color, fill_color=fill_color, fill_opacity=fill_opacity: {
                "fillColor": fill_color,
                "color": color,
                "weight": 2,
                "fillOpacity": fill_opacity,
            },
            tooltip=folium.Tooltip(tooltip_html, max_width=250),
            popup=folium.Popup(popup_html, max_width=450)
        ).add_to(m)
    
    return m


def create_gigs_table(gigs_data: list) -> pd.DataFrame:
    """Create pandas DataFrame for gigs table"""
    if not gigs_data:
        return pd.DataFrame()
    
    # Prepare data for table
    table_data = []
    for gig in gigs_data:
        date_str = ""
        if gig.get("parsed_date"):
            parsed_date = gig["parsed_date"]
            if isinstance(parsed_date, str):
                try:
                    parsed_date = datetime.fromisoformat(parsed_date.replace('Z', '+00:00'))
                    date_str = parsed_date.strftime("%d.%m.%Y %H:%M")
                except:
                    date_str = gig.get("date", "") + ' ' + gig.get("time", "")
            else:
                date_str = parsed_date.strftime("%d.%m.%Y %H:%M")
        
        # Create band info with thumbnail and clickable link
        band_name = gig.get("band_name", "Unknown Band")
        band_id = gig.get("band", {}).get("id") if isinstance(gig.get("band"), dict) else gig.get("band_id")
        thumbnail_url = gig.get("band_image_thumb", "")
        
        # Create combined band cell with thumbnail + name + link
        band_html = ""
        if thumbnail_url:
            band_html += f'<img src="{thumbnail_url}" style="width:30px;height:30px;object-fit:cover;margin-right:8px;vertical-align:middle;" alt="Band thumbnail">'
        
        if band_id:
            band_html += f'<a href="https://mx3.ch/{band_id}" target="_blank" style="color: #0066cc; text-decoration: none;">{band_name}</a>'
        else:
            band_html += band_name
        
        table_data.append({
            "Date": date_str,
            "Band": band_html,
            "Venue": gig.get("venue", ""),
            "Location": gig.get("location", ""),
            "Canton": gig.get("canton", ""),
            "Categories": ", ".join(gig.get("band_categories", []))
        })
    
    df = pd.DataFrame(table_data)
    return df


@st.cache_data(ttl=3600)
def load_preprocessed_data():
    """Load pre-processed data files for instant app startup."""
    logger.info("Loading pre-processed data...")
    
    try:
        # Load processed gigs
        with open('data/processed_gigs.json', 'r') as f:
            processed_gigs = json.load(f)
        
        # Load municipality gigs mapping
        with open('data/municipality_gigs.json', 'r') as f:
            municipality_gigs = json.load(f)
        
        # Load simplified geo data (only municipalities with gigs)
        with open('data/simplified_geo.json', 'r') as f:
            geo_data = json.load(f)
        
        # Load metadata
        with open('data/metadata.json', 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"Loaded {metadata['total_gigs']} gigs from {metadata['municipalities_with_gigs']} municipalities")
        return processed_gigs, geo_data, municipality_gigs, metadata
        
    except FileNotFoundError:
        st.error("Pre-processed data not found. Please run: python preprocess_data.py")
        st.stop()
    except Exception as e:
        st.error(f"Error loading pre-processed data: {e}")
        st.stop()


def main():
    """Main Streamlit application"""
    st.title(APP_TITLE)
    st.markdown(f"*{APP_DESCRIPTION}*")
    
    # Load data
    try:
        processed_gigs, geo_data, municipality_gigs, metadata = load_preprocessed_data()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.stop()
    
    # Stats
    total_gigs = len(processed_gigs)
    total_municipalities_with_gigs = len(municipality_gigs)
    total_municipalities = metadata.get('total_municipalities', 2175)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Gigs", total_gigs)
    with col2:
        st.metric("Municipalities with Gigs", total_municipalities_with_gigs)
    with col3:
        st.metric("Coverage", f"{total_municipalities_with_gigs}/{total_municipalities}")
    
    # Map section (full width)
    st.subheader("🗺️ Interactive Map")
    
    # Create and display map
    try:
        map_obj = create_interactive_map(municipality_gigs, geo_data)
        st_folium(map_obj, width=None, height=500)
    except Exception as e:
        import traceback
        st.error(f"Failed to create map: {e}")
        st.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Map creation error: {e}")
        logger.error(traceback.format_exc())
    
    # Table section (below map)
    st.subheader("📋 Gigs Table")
    
    # Search functionality
    search_term = st.text_input("🔍 Search bands or locations", "")
    
    # Filter data based on search
    filtered_gigs = processed_gigs
    if search_term:
        search_lower = search_term.lower()
        filtered_gigs = [
            gig for gig in processed_gigs
            if (search_lower in (gig.get("band_name", "").lower())) or
               (search_lower in (gig.get("location", "").lower())) or
               (search_lower in (gig.get("venue", "").lower()))
        ]
    
    # Create and display table
    if filtered_gigs:
        df = create_gigs_table(filtered_gigs)
        
        # Display table with proper formatting
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No gigs found matching your search")
    
    # Sidebar with additional info
    with st.sidebar:
        st.header("ℹ️ Information")
        st.markdown("This app visualizes live music gigs across Switzerland using official data.")
        
        st.subheader("Legend")
        st.markdown("""
        - **Red municipalities**: Have upcoming gigs
        - **Gray municipalities**: No upcoming gigs  
        - **Hover** over municipalities to see gig details
        - **Click** band names to visit their profiles
        """)
        
        if processed_gigs:
            latest_update = max([gig.get("parsed_date") for gig in processed_gigs if gig.get("parsed_date")])
            if latest_update:
                st.markdown(f"**Latest gig:** {latest_update.strftime('%d.%m.%Y')}")
        
        # Data refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()