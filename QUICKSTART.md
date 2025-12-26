# Quick Start Guide

Get your Marketing Campaign Tracker up and running in minutes!

## Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] Google Ads account with active campaigns
- [ ] Google Ads API credentials ready

## Step-by-Step Setup

### 1. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and add your Google Ads API credentials:

```bash
GOOGLE_ADS_DEVELOPER_TOKEN=your_token_here
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_secret_here
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=1234567890
```

### 2. Build and Run

```bash
# Build and start all services
docker-compose up --build
```

Wait for the build to complete. You'll see output like:
```
backend_1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend_1  | nginx: [notice] nginx/1.x.x
```

### 3. Access the Application

Open your browser and navigate to:
- **Application**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### 4. Verify It Works

You should see:
1. A list of your active Google Ads campaigns
2. Current metrics (spend, CTR, conversions) for each campaign
3. Interactive charts showing trends over the last 7 days

## Troubleshooting First Run

### "Failed to load campaigns"

**Check your credentials:**
```bash
# View backend logs
docker-compose logs backend

# Look for authentication errors
```

**Common fixes:**
- Verify Customer ID is correct (no hyphens)
- Ensure refresh token is valid
- Check developer token is approved or using test account

### Can't connect to localhost:3000

**Check services are running:**
```bash
docker-compose ps
```

Both services should show "Up" status.

**Restart services:**
```bash
docker-compose down
docker-compose up
```

### No campaigns showing but no errors

- Verify your Google Ads account has campaigns with status ENABLED or PAUSED
- Check that campaigns have data in the last 7 days
- Ensure API permissions are correctly set in Google Cloud Console

## Development Mode

For local development without Docker:

### Backend
```bash
cd backend
poetry install
cp .env.example .env
# Edit .env with credentials
poetry run python -m app.main
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Next Steps

- Customize the date range in the components
- Add Meta Ads or Reddit Ads adapters
- Deploy to your VPS (see README.md)
- Set up monitoring and alerts

## Getting Help

- Read the full [README.md](README.md) for detailed documentation
- Check Google Ads API [documentation](https://developers.google.com/google-ads/api/docs/start)
- Review [API documentation](http://localhost:8000/docs) when backend is running

Happy monitoring! 🚀
