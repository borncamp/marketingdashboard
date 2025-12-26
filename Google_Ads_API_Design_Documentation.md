# Marketing Campaign Tracker - Design Documentation

## Application Overview

**Application Name:** Marketing Campaign Tracker
**Purpose:** Self-service marketing analytics dashboard for monitoring Google Ads campaign performance
**Developer:** Personal/Internal Use
**Date:** December 2025

## Executive Summary

Marketing Campaign Tracker is a web-based analytics dashboard designed to provide real-time visibility into Google Ads campaign performance. The application enables users to monitor campaign metrics, track spending, and analyze performance trends through an intuitive web interface.

## Application Architecture

### Technology Stack

- **Backend:** Python 3.11+ with FastAPI framework
- **Frontend:** React with TypeScript
- **Deployment:** Docker containerized application on VPS
- **Security:** OAuth 2.0 authentication with encrypted credential storage

### System Components

```
┌─────────────────┐
│   Web Browser   │
│   (React UI)    │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  FastAPI Server │
│   (Python)      │
└────────┬────────┘
         │ Google Ads API
         ▼
┌─────────────────┐
│  Google Ads API │
│   (Production)  │
└─────────────────┘
```

## Core Functionality

### 1. Campaign Monitoring
- **Display active campaigns** with current status (Enabled/Paused/Removed)
- **Real-time metrics** including spend, CTR, conversions, and impressions
- **Multi-campaign view** for portfolio-level analysis

### 2. Performance Analytics
- **Time-series visualization** showing 7-day, 30-day, and custom date range trends
- **Metric comparison** across campaigns and time periods
- **Spend tracking** with budget utilization insights

### 3. Data Visualization
- **Interactive charts** using Recharts library for line graphs and trend analysis
- **Responsive design** for desktop and mobile viewing
- **Export capabilities** for reporting purposes

## API Usage and Data Flow

### Authentication Flow
1. User provides OAuth 2.0 credentials via secure onboarding wizard
2. Application exchanges authorization code for refresh token
3. Credentials stored encrypted (AES-256 via Fernet) on server
4. Refresh token used to obtain access tokens for API calls

### Data Retrieval Process
1. **Campaign List Retrieval**
   - Endpoint: `GoogleAdsService.search()`
   - Query: SELECT campaign data with status filters
   - Frequency: On-demand user requests

2. **Metrics Collection**
   - Endpoint: `GoogleAdsService.search()` with metrics fields
   - Metrics: Cost, CTR, conversions, impressions, clicks
   - Date Range: Last 7-30 days (configurable)
   - Frequency: Real-time queries (no caching)

3. **Customer Information**
   - Endpoint: `CustomerService.listAccessibleCustomers()`
   - Purpose: Account validation and manager account discovery

### API Request Volume Estimate
- **Average daily requests:** ~50-100 API calls
- **Peak usage:** ~200 requests during active monitoring sessions
- **Request types:**
  - Campaign list queries: 10-20/day
  - Metrics queries: 30-60/day
  - Account validation: 5-10/day

## Data Storage and Privacy

### Data Handling Policy
- **No persistent storage** of campaign data or metrics
- **Credentials only:** OAuth tokens and API credentials stored encrypted
- **Session-based:** All campaign data displayed in real-time from API
- **User control:** Users can clear credentials at any time

### Security Measures
1. **Encryption at rest:** Fernet (symmetric encryption) for stored credentials
2. **HTTPS only:** All web traffic encrypted with Let's Encrypt SSL
3. **OAuth 2.0:** Industry-standard authorization framework
4. **No third-party sharing:** Data never transmitted to external services

## User Experience Flow

### Initial Setup
1. User navigates to web application
2. Completes onboarding wizard:
   - Enters Developer Token from Google Ads API Center
   - Provides OAuth Client ID and Secret from Google Cloud Console
   - Enters Customer ID from Google Ads account
   - Authorizes application via Google OAuth consent screen
3. Application validates credentials via test API call
4. Settings saved encrypted for future sessions

### Daily Usage
1. User logs into dashboard
2. Application loads campaign list from Google Ads API
3. User selects campaigns to analyze
4. Charts and metrics populate with real-time data
5. User can filter by date range, campaign status, or metric type

## Compliance and Best Practices

### Google Ads API Terms of Service
- **Read-only access:** Application only retrieves data, never modifies campaigns
- **Personal use:** Used solely by the account owner for their own data
- **No resale:** Data not used for commercial purposes or resold
- **Proper attribution:** Google Ads branding displayed where required

### Rate Limiting and Resource Management
- **Respectful API usage:** Implements exponential backoff for errors
- **Efficient queries:** Uses field masks to request only needed data
- **No polling:** Queries triggered only by user actions, not automated polling

### User Access Control
- **Single-user application:** Designed for individual account owners
- **No multi-tenancy:** Each deployment serves one Google Ads account
- **Credential isolation:** Each user manages their own credentials

## Technical Implementation Details

### Key API Calls Used

**1. List Campaigns**
```sql
SELECT
  campaign.id,
  campaign.name,
  campaign.status
FROM campaign
WHERE campaign.status != 'REMOVED'
```

**2. Retrieve Metrics**
```sql
SELECT
  campaign.id,
  campaign.name,
  metrics.cost_micros,
  metrics.ctr,
  metrics.conversions,
  metrics.impressions,
  metrics.clicks
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
```

**3. Validate Account Access**
```python
customer_service.list_accessible_customers()
```

### Error Handling
- **API errors:** Graceful degradation with user-friendly error messages
- **Authentication failures:** Clear instructions for credential refresh
- **Rate limiting:** Automatic retry with exponential backoff
- **Network issues:** Timeout handling and connection retry logic

## Maintenance and Support

### Update Cadence
- **Security patches:** Applied within 24 hours of release
- **API version updates:** Quarterly review and updates
- **Feature enhancements:** As needed based on Google Ads API changes

### Monitoring
- **Application health:** Automated health checks via `/health` endpoint
- **API quota usage:** Monitored to stay within limits
- **Error logging:** Server-side logging for debugging

## Future Enhancements

### Planned Features
1. **Multi-platform support:** Expand to Meta Ads and Reddit Ads
2. **Automated reports:** Scheduled email reports with key metrics
3. **Budget alerts:** Notifications when spending exceeds thresholds
4. **Performance insights:** AI-powered recommendations for optimization

### Scalability
- Architecture designed with adapter pattern for easy platform additions
- Database integration planned for historical trend analysis
- API caching layer for improved performance at scale

## Conclusion

Marketing Campaign Tracker provides a secure, efficient, and user-friendly interface for monitoring Google Ads campaign performance. The application adheres to Google Ads API best practices, respects user privacy, and delivers real-time insights through a modern web interface.

---

**Contact Information:**
For questions or additional information about this application, please contact the developer through the Google Ads API support channels.

**Application URL:** https://marketing.brianborncamp.com
**Documentation Version:** 1.0
**Last Updated:** December 25, 2025
