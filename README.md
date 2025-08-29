# Swiss Bandmap

Interactive visualization of live music gigs across Swiss municipalities using official music platform data.

## Features

- 🗺️ **Interactive Map**: Hover over municipalities to see upcoming gigs
- 🌡️ **Heatmap**: Color-coded municipalities by gig density
- 📋 **Searchable Table**: Look up artists or locations
- 🔗 **Direct Links**: Click artist names to visit their profiles
- 🖼️ **Thumbnails**: Display artist images from the music platform

## Local Development

### Prerequisites

- Python 3.11+
- API credentials (consumer key and secret)

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

### Data Sources

- **Gig Data**: Official Swiss music platform API
- **Geographic Data**: Swiss Federal Statistical Office municipalities

## Deployment

### Google Cloud Run (with Auto-Fresh Data)

1. **Prerequisites**:
   - Google Cloud account with billing enabled
   - `gcloud` CLI installed and authenticated  
   - Docker installed
   - API credentials in `.env` file

2. **Configure deployment**:
   ```bash
   # Edit deploy.sh and set your PROJECT_ID
   vim deploy.sh
   ```

3. **Deploy**:
   ```bash
   ./deploy.sh
   ```

#### Data Freshness System
- **Build-time**: Fresh data fetched during Docker build
- **Runtime**: Auto-refresh when data >24 hours old  
- **User Experience**: Always instant loading with ≤48 hour old data
- **Zero overhead**: No additional GCP services required

### Testing
```bash
./test.sh  # Run unit tests
```

### Environment Variables

- `CONSUMER_KEY`: API consumer key
- `CONSUMER_SECRET`: API consumer secret

## Architecture

- **Frontend**: Streamlit web framework
- **Maps**: Folium for interactive visualization  
- **Data**: In-memory caching with 1-hour TTL
- **Deployment**: Containerized on Google Cloud Run

## Performance Optimizations

- Simplified GeoJSON for faster rendering
- Cached API responses to minimize external calls
- Efficient municipality name matching with fuzzy logic
- Lightweight container image

## License

This project is for demonstration purposes.