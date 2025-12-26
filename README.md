# Marketing Campaign Tracker

A web application for monitoring and analyzing marketing campaigns across multiple advertising platforms in real-time. Currently supports Google Ads with a flexible architecture for adding Meta Ads and Reddit Ads.

## Features

- **Real-time Campaign Monitoring**: View all your campaigns with current status and metrics
- **Performance Metrics**: Track spend, CTR (Click-Through Rate), and conversions
- **Interactive Charts**: Visualize metric trends over time with interactive line charts
- **Multi-Platform Ready**: Extensible architecture supports multiple ad platforms
- **Dockerized Deployment**: Easy deployment with Docker and Docker Compose

## Tech Stack

### Backend
- **Python 3.11+** with Poetry for dependency management
- **FastAPI** for high-performance REST API
- **Google Ads API** for campaign data integration
- **Pydantic** for data validation and settings management

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and optimized builds
- **TailwindCSS** for modern, responsive styling
- **Recharts** for beautiful data visualizations

### Infrastructure
- **Docker & Docker Compose** for containerization
- **Nginx** for serving frontend and reverse proxy

## Project Structure

```
marketing/
├── backend/
│   ├── app/
│   │   ├── models/          # Data models (Campaign, Metric, etc.)
│   │   ├── services/        # Ad platform adapters (Google Ads, etc.)
│   │   ├── routers/         # API endpoints
│   │   ├── config.py        # Configuration management
│   │   └── main.py          # FastAPI application
│   ├── pyproject.toml       # Poetry dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API client
│   │   ├── types/           # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml       # Full stack orchestration
└── README.md
```

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Google Ads API credentials (see setup guide below)
- Node.js 18+ and Python 3.11+ (for local development)

### Google Ads API Setup

Before running the application, you need to set up Google Ads API credentials:

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Google Ads API**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Ads API" and enable it

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the credentials JSON file

4. **Get Developer Token**
   - Visit [Google Ads API Center](https://ads.google.com/aw/apicenter)
   - Apply for a developer token (you can use test account initially)

5. **Generate Refresh Token**
   ```bash
   # Install google-ads library
   pip install google-ads

   # Run the authentication helper
   python -m google.ads.googleads.generate_refresh_token \
     --client_id YOUR_CLIENT_ID \
     --client_secret YOUR_CLIENT_SECRET
   ```
   Follow the prompts and save the refresh token

6. **Get Customer ID**
   - Log into your Google Ads account
   - Find your Customer ID (10 digits, without hyphens)

### Installation & Deployment

1. **Clone the repository**
   ```bash
   cd /path/to/marketing
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your Google Ads API credentials
   ```

3. **Set authentication credentials**
   ```bash
   # Use the interactive password setter (recommended)
   ./set-password.sh

   # Or set them directly in .env
   # AUTH_USERNAME=your_username
   # AUTH_PASSWORD=your_secure_password
   ```

4. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

   The application uses HTTP Basic Authentication. Your browser will prompt for the username and password you set in step 3.

### Local Development

#### Backend Development

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Run the development server
poetry run python -m app.main
```

The backend will be available at http://localhost:8000

#### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Copy and configure environment variables
cp .env.example .env

# Run the development server
npm run dev
```

The frontend will be available at http://localhost:3000

## API Endpoints

### Campaign Endpoints

- `GET /api/campaigns` - Get all campaigns with current metrics
- `GET /api/campaigns/{campaign_id}/metrics/{metric_name}?days=7` - Get time series data for a specific metric

#### Supported Metrics
- `spend` - Total advertising spend in USD
- `ctr` - Click-through rate as percentage
- `conversions` - Total number of conversions

### Example Response

```json
{
  "campaign_id": "123456789",
  "campaign_name": "Summer Sale Campaign",
  "metric_name": "spend",
  "unit": "USD",
  "data_points": [
    {"date": "2024-01-01", "value": 125.50},
    {"date": "2024-01-02", "value": 143.25}
  ]
}
```

## Architecture

### Adapter Pattern

The application uses an adapter pattern to support multiple ad platforms:

```python
class AdPlatformAdapter(ABC):
    @abstractmethod
    async def get_campaigns(self) -> List[Campaign]:
        pass

    @abstractmethod
    async def get_campaign_metrics(
        self, campaign_id: str, metric_name: str, days: int = 7
    ) -> TimeSeriesData:
        pass
```

This makes it easy to add new platforms:
1. Create a new adapter class (e.g., `MetaAdsAdapter`, `RedditAdsAdapter`)
2. Implement the required methods
3. Register the adapter in the API router

### Data Models

Platform-agnostic data models ensure consistent API responses:

- **Campaign**: Basic campaign information with status and metrics
- **Metric**: Individual metric with name, value, and unit
- **TimeSeriesData**: Historical data points for charting
- **DataPoint**: Single date-value pair in time series

## Deployment

### VPS Deployment

1. **Set up your VPS**
   ```bash
   # Install Docker and Docker Compose
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```

2. **Clone and configure**
   ```bash
   git clone <your-repo-url>
   cd marketing
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Set authentication credentials**
   ```bash
   # Option 1: Set password remotely from your local machine
   ./set-remote-password.sh

   # Option 2: Set password directly on the server
   ssh your-server
   cd /opt/marketing-tracker
   ./set-password.sh
   ```

4. **Deploy**
   ```bash
   docker-compose up -d
   ```

5. **Set up reverse proxy (optional)**
   - Use nginx or Caddy to proxy to port 3000
   - Configure SSL with Let's Encrypt

### Security Best Practices

- **Never commit credentials**: The `.env` file is automatically ignored by git
- **Change default password**: Use `./set-password.sh` to set a strong password (8+ characters recommended)
- **Rotate passwords regularly**: Use `./set-remote-password.sh` to update production passwords without SSH access
- **Use HTTPS**: Always use SSL/TLS in production (configured via reverse proxy)

## Future Enhancements

- [ ] Add Meta Ads integration
- [ ] Add Reddit Ads integration
- [ ] Add date range picker for custom time periods
- [ ] Implement data caching to reduce API calls
- [ ] Add campaign comparison view
- [ ] Add email alerts for budget thresholds
- [ ] Implement user authentication
- [ ] Add export functionality (CSV, PDF reports)
- [ ] Support multiple ad accounts

## Troubleshooting

### Common Issues

**Backend fails to start**
- Check that all Google Ads API credentials are correctly set in `.env`
- Verify your developer token is approved (or use test account)
- Check Docker logs: `docker-compose logs backend`

**No campaigns showing**
- Verify your Google Ads account has active campaigns
- Check that Customer ID is correct (10 digits, no hyphens)
- Review API permissions in Google Cloud Console

**Frontend can't connect to backend**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/config.py`
- Verify network connectivity in Docker: `docker network inspect marketing_marketing-network`

## Contributing

Contributions are welcome! To add support for a new ad platform:

1. Create a new adapter in `backend/app/services/`
2. Implement the `AdPlatformAdapter` interface
3. Add configuration for the new platform
4. Update the router to support the new platform
5. Test thoroughly with real account data
6. Submit a pull request

## License

MIT License - feel free to use this project for your own campaigns!

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review Google Ads API [documentation](https://developers.google.com/google-ads/api/docs/start)
- Open an issue in the repository
