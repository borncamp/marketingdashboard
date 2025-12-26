# Marketing Campaign Tracker - Quick Start

## 🚀 Two Ways to Get Started

### Option 1: Google Ads Scripts (Recommended for Quick Setup)

**Best for:** Instant setup, no approval needed

1. **Deploy the application**:
   ```bash
   ./deploy-production.sh
   ```

2. **Set up Google Ads Script**:
   - Follow the guide: [GOOGLE_ADS_SCRIPT_SETUP.md](./GOOGLE_ADS_SCRIPT_SETUP.md)
   - Takes 5 minutes
   - No API approval needed!

3. **Access your dashboard**:
   - Visit https://marketing.brianborncamp.com
   - Data syncs automatically on your schedule

### Option 2: Direct Google Ads API (For Advanced Users)

**Best for:** Real-time data, large scale operations

1. **Apply for Google Ads API Basic Access**:
   - Submit design documentation (included: `Google_Ads_API_Design_Documentation.md`)
   - Wait 24-48 hours for approval

2. **Complete onboarding**:
   - Visit https://marketing.brianborncamp.com
   - Follow the onboarding wizard
   - Enter your API credentials

## Architecture Comparison

| Feature | Google Ads Scripts | Direct API |
|---------|-------------------|------------|
| Setup Time | 5 minutes | 24-48 hours |
| Approval Required | ❌ No | ✅ Yes |
| Data Freshness | Scheduled (hourly/daily) | Real-time |
| Best For | Personal dashboards | Enterprise apps |

## What You Get

- 📊 **Campaign Overview**: See all your campaigns at a glance
- 💰 **Spend Tracking**: Monitor advertising costs
- 📈 **Performance Metrics**: CTR, conversions, impressions
- 📉 **Trend Charts**: 7-30 day historical data
- 🔄 **Auto-Sync**: Scheduled updates (Scripts) or real-time (API)

## Project Structure

```
marketing/
├── backend/           # FastAPI server
│   ├── app/
│   │   ├── database.py      # SQLite data storage
│   │   ├── routers/
│   │   │   ├── campaigns.py # Campaign API
│   │   │   ├── settings.py  # Configuration
│   │   │   └── sync.py      # Data sync endpoint
│   │   └── main.py
│   └── data/          # SQLite database (auto-created)
├── frontend/          # React dashboard
├── google-ads-script.js      # Script to paste in Google Ads
└── deploy-production.sh      # Deployment script
```

## Quick Commands

### Deploy to Production
```bash
./deploy-production.sh
```

### Check Application Status
```bash
curl https://marketing.brianborncamp.com/health
```

### Check Sync Status (Scripts mode)
```bash
curl https://marketing.brianborncamp.com/api/sync/status
```

### View Backend Logs
```bash
ssh root@46.224.115.100 "cd /opt/marketing-tracker && docker-compose logs -f backend"
```

### Restart Services
```bash
ssh root@46.224.115.100 "cd /opt/marketing-tracker && docker-compose restart"
```

## Documentation Files

- **[GOOGLE_ADS_SCRIPT_SETUP.md](./GOOGLE_ADS_SCRIPT_SETUP.md)** - Complete guide for Scripts approach
- **[Google_Ads_API_Design_Documentation.md](./Google_Ads_API_Design_Documentation.md)** - Design doc for API approval
- **[google-ads-script.js](./google-ads-script.js)** - Script to paste in Google Ads

## Troubleshooting

### Scripts Not Syncing?

1. Check Google Ads Scripts logs
2. Verify API endpoint is accessible:
   ```bash
   curl -X POST https://marketing.brianborncamp.com/api/sync/push \
     -H "Content-Type: application/json" \
     -d '{"campaigns":[],"source":"test"}'
   ```
3. Should return: `{"success":true,...}`

### Dashboard Shows No Data?

1. Check sync status: https://marketing.brianborncamp.com/api/sync/status
2. Run the Google Ads Script manually once
3. Check backend logs for errors

### Need to Switch Between Approaches?

The app supports both! You can:
- Start with Scripts for immediate access
- Later add API credentials for real-time data
- Use whichever source you prefer

## Tech Stack

- **Backend**: Python (FastAPI), SQLite
- **Frontend**: React, TypeScript, Recharts
- **Deployment**: Docker, Nginx, Let's Encrypt SSL
- **Data Sources**: Google Ads Scripts OR Google Ads API

## License

MIT

## Support

- Google Ads Scripts Docs: https://developers.google.com/google-ads/scripts
- Google Ads API Docs: https://developers.google.com/google-ads/api
- FastAPI Docs: https://fastapi.tiangolo.com
