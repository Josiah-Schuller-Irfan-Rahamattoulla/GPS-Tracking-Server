# Cell Location Setup Guide

## Why Cell Location?

Cell tower positioning provides **instant location** (1-2 seconds) without GPS:
- **Accuracy**: 100m - 2km depending on cell density
- **Works indoors** where GPS fails
- **Low power** - no GPS radio needed
- **Instant** - as fast as LTE connection

Perfect for:
1. Quick "where is my device?" checks
2. Indoor tracking
3. Initial position before GPS fix
4. Providing lat/lon to A-GNSS for faster GPS acquisition

## Provider Options

### 1. Google Geolocation API (Recommended for Australia)

**Pros:**
- Best coverage in Australia
- Most accurate in urban areas
- 40,000 free requests/month
- Well-documented

**Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project or select existing one
3. Enable **Geolocation API**:
   - Navigate to "APIs & Services" > "Library"
   - Search "Geolocation API"
   - Click "Enable"
4. Create API Key:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy your API key
5. (Optional) Restrict API key:
   - Click on your API key
   - Under "API restrictions", select "Restrict key"
   - Select only "Geolocation API"
   - Under "Application restrictions", add your server IP

**Configuration:**
```bash
# In .env file
CELL_LOCATION_PROVIDER=google
GOOGLE_GEOLOCATION_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXX
```

**Pricing:**
- Free tier: 40,000 requests/month
- Additional: $5 per 1,000 requests
- For 100 devices checking every 5 minutes: ~864,000 req/month = $41/month

### 2. HERE Positioning API

**Pros:**
- Good global coverage
- Accurate in Europe and Asia
- 250,000 free transactions/month

**Setup:**
1. Go to [HERE Developer Portal](https://developer.here.com/)
2. Sign up for free account
3. Create new project
4. Generate API Key
5. Copy API key

**Configuration:**
```bash
# In .env file
CELL_LOCATION_PROVIDER=here
HERE_API_KEY=YOUR_HERE_API_KEY
```

**Pricing:**
- Free tier: 250,000 requests/month
- Additional: $1 per 1,000 requests

### 3. nRF Cloud Location Services (Default)

**Pros:**
- Same API as A-GNSS (already configured)
- No additional setup needed
- Decent global coverage

**Cons:**
- Lower accuracy than Google in some regions
- May return very large accuracy radius for unknown cells

**Configuration:**
```bash
# In .env file
CELL_LOCATION_PROVIDER=nrf_cloud
NRF_CLOUD_API_KEY=your_existing_key
```

**Already configured!** Uses the same key as A-GNSS.

## AWS Location Service Integration

AWS Location Service can also provide cell positioning, but it's more complex:

**Setup Required:**
1. AWS account with Location Service enabled
2. Amazon Location Service Place Index
3. IAM role with geo:SearchPlaceIndex permissions
4. AWS SDK integration in Python

**Would need additional implementation:**
```python
import boto3

async def get_aws_location(cells: List[CellInfo], region: str):
    client = boto3.client('location', region_name=region)
    # AWS Location Service API calls
    ...
```

**Cost:** $4 per 1,000 requests (more expensive than Google/HERE free tiers)

## Current Status

✅ **Server endpoint implemented**: `/v1/cell_location`
✅ **Supports 3 providers**: nRF Cloud, Google, HERE
⚠️ **Google API key needed**: Add to `.env` file
❌ **Firmware not implemented yet**: Needs `lte_lc_cells_info_get()` call

## Testing

Once you have a Google API key:

```powershell
# Update .env with your key
$env:GOOGLE_GEOLOCATION_API_KEY = "AIzaSyXXXXXXX"

# Rebuild and restart
docker-compose build api
docker-compose up -d api

# Test with Australian cell data
.\test-cell-location-australia.ps1
```

## Next Steps

1. **Get Google API key** (5 minutes)
2. **Add to `.env`** and restart server
3. **Implement firmware side**:
   - Call `lte_lc_cells_info_get()` after LTE connects
   - HTTP POST to `/v1/cell_location`
   - Parse response for instant lat/lon
4. **Use position for A-GNSS** request to speed up GPS

## Firmware Integration (Coming Next)

```c
// In modem.c after LTE connection established
struct lte_lc_cells_info cells_info = {0};
int err = lte_lc_cells_info_get(&cells_info);

if (err == 0 && cells_info.current_cell.id != 0) {
    // Build JSON payload
    char payload[512];
    snprintf(payload, sizeof(payload),
        "{\"cells\":[{\"cellId\":%d,\"mcc\":%d,\"mnc\":%d,"
        "\"tac\":%d,\"signal\":%d}],\"device_id\":%d}",
        cells_info.current_cell.id,
        cells_info.current_cell.mcc,
        cells_info.current_cell.mnc,
        cells_info.current_cell.tac,
        cells_info.current_cell.rsrp,
        DEVICE_ID
    );
    
    // HTTP POST to server
    server_post_cell_location(payload);
}
```

Response gives you instant position!
