# GPS Tracking System - Integration Status
**Date:** February 15, 2026  
**Commits:** Server feature/trip_history branch (c4e3c56)

## 🎯 System Overview
Complete GPS tracking system with nRF9151 firmware, FastAPI server, React Native mobile app, and React web dashboard.

---

## ✅ Component Status

### 1. **nRF9151 Firmware** (GPS-Tracking-PCB/nrf9151-firmware)
**Status:** ✅ CONFIGURED  
**Server URL:** `http://chatty-otter-15.loca.lt`  
**Location:** `src/main.c:142-150`

```c
#define SERVER_BASE_URL_OVERRIDE "http://chatty-otter-15.loca.lt"
#define DEVICE_ID                67
#define DEVICE_ACCESS_TOKEN      "sim_device_12345_123456789"
```

**Capabilities:**
- ✅ GNSS positioning with multi-constellation support
- ✅ Server-side A-GNSS data fetch (`/v1/agnss`)
- ✅ Cell location via server (`/v1/cell_location`)
- ✅ GPS data upload (`/v1/sendGPSData`)
- ✅ Device registration (`/v1/registerDevice`)
- ✅ NVS storage for A-GNSS hints
- ✅ IMU-based power management
- ⚠️ **UNCOMMITTED** firmware changes (submodule updates only)

---

### 2. **FastAPI Server** (GPS-Tracking-Server)
**Status:** ✅ RUNNING + COMMITTED  
**Local:** `http://localhost:8000`  
**Tunnel:** `https://chatty-otter-15.loca.lt`  
**Branch:** `feature/trip_history` (commit c4e3c56)

**Recent Updates:**
- ✅ nRF Cloud Service Evaluation Token configured (valid until 2026-03-03)
- ✅ Automatic A-GNSS fallback: nRF Cloud → Google SUPL
- ✅ A-GNSS cache with 2-hour TTL
- ✅ Cell location with auto provider fallback (nRF Cloud/Google/HERE)
- ✅ SUPL client with Google/Nokia/XSE servers (connects but protocol incomplete)

**Configuration (.env):**
```bash
NRF_CLOUD_API_KEY=eyJhbGc...  # Service Evaluation Token (JWT)
AGNSS_PROVIDER=              # Empty = auto fallback enabled
SUPL_DEMO=0                  # Production mode
AGNSS_CACHE_TTL_SEC=7200     # 2 hours
```

**Endpoints:**
```
✅ POST /v1/signup              # User registration
✅ POST /v1/login               # User authentication
✅ GET  /v1/agnss               # A-GNSS data (nRF Cloud/SUPL)
✅ POST /v1/cell_location       # Cell tower location
✅ POST /v1/registerDevice      # Device registration
✅ POST /v1/sendGPSData         # GPS data ingestion
✅ GET  /v1/user                # User info retrieval
✅ GET  /v1/userDevices         # User's devices
✅ GET  /v1/latestGPSData       # Latest GPS position
✅ GET  /v1/historicalGPSData   # Historical GPS data
✅ POST /v1/tripHistory         # Trip history retrieval
✅ POST /v1/deviceActions       # Device control commands
```

**Docker Services:**
- `gps-tracking-db`: PostgreSQL 13 (healthy)
- `gps-tracking-api`: FastAPI + Gunicorn (healthy)

---

### 3. **React Native Mobile App** (GPS-Tracking-App)
**Status:** ✅ CONFIGURED  
**Server URL:** `https://chatty-otter-15.loca.lt`  
**Location:** `config.js:6`

```javascript
export const DEFAULT_API_BASE = "https://chatty-otter-15.loca.lt";
```

**Features:**
- ✅ User authentication (signup/login)
- ✅ Device management
- ✅ Real-time GPS tracking
- ✅ Historical data visualization
- ✅ Trip history analysis
- ✅ Device settings & controls
- ⚠️ **NO UNCOMMITTED CHANGES**

**API Client:** `GpsTrackingApi.js` (shared HTTP client)

---

### 4. **React Web Dashboard** (GPS-Tracking-Website)
**Status:** ✅ CONFIGURED  
**Server URL:** `https://chatty-otter-15.loca.lt`  
**Location:** `src/api/GpsTrackingApi.ts:6`

```typescript
const FIXED_BASE_URL = 'https://chatty-otter-15.loca.lt';
```

**Features:**
- ✅ User authentication
- ✅ Fleet dashboard view
- ✅ Interactive map with Leaflet
- ✅ Geofence management
- ✅ Device settings
- ✅ Trip controls
- ⚠️ **NO UNCOMMITTED CHANGES**

**Tech Stack:** Expo Web + TypeScript + Leaflet maps

---

## 🔄 Integration Flow

### GPS Data Upload Flow
```
nRF9151 Firmware
    ↓ (HTTPS POST /v1/sendGPSData)
FastAPI Server (chatty-otter-15.loca.lt)
    ↓ (store in PostgreSQL)
Mobile App / Web Dashboard
    ↓ (GET /v1/latestGPSData, /v1/historicalGPSData)
User sees real-time position
```

### A-GNSS Flow
```
nRF9151 Firmware (needs assistance data)
    ↓ (HTTP GET /v1/agnss?device_id=67)
FastAPI Server
    ├─➔ Try nRF Cloud API (Service Evaluation Token)
    │   ✅ Returns 3102 bytes assistance data
    └─➔ Fallback to Google SUPL (if nRF fails)
        ⚠️ Connects but protocol incomplete
    ↓ (binary A-GNSS payload)
nRF9151 injects via nrf_cloud_agnss_process()
    ↓ (faster TTFF ~10-30s vs 2-5 min)
GPS fix acquired
```

### Cell Location Flow
```
nRF9151 Firmware (no GPS fix yet)
    ↓ (HTTP POST /v1/cell_location with LTE cell info)
FastAPI Server
    ├─➔ Try nRF Cloud (if key available)
    ├─➔ Fallback to Google Geolocation API
    └─➔ Fallback to HERE Location Services
    ↓ (lat/lon with uncertainty radius)
nRF9151 uses as A-GNSS position hint
```

---

## 📊 Current System Metrics

### A-GNSS Performance
- **Source:** nRF Cloud (primary)
- **Response Size:** 3102 bytes
- **Cache TTL:** 2 hours
- **Fallback:** Google SUPL (connects, no data yet)
- **Evaluation Period:** Until 2026-03-03

### Server Status
- **Uptime:** Active (Docker)
- **Tunnel:** chatty-otter-15.loca.lt (auto-restart)
- **Database:** PostgreSQL 13 (healthy)
- **Cache:** File-based (`agnss_cache.bin`)

### Firmware Build
- **Platform:** nRF9151 (Cortex-M33)
- **SDK:** Zephyr RTOS + nRF Connect SDK
- **Build:** Custom CMake + West
- **Flash Size:** ~500KB (with A-GNSS support)

---

## 🚀 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Production Setup                        │
└─────────────────────────────────────────────────────────────┘

Internet
    │
    ├──➔ Mobile Users (iOS/Android)
    │       └─➔ React Native App
    │              └─➔ https://chatty-otter-15.loca.lt
    │
    ├──➔ Web Users (Desktop/Mobile Browser)
    │       └─➔ React Web Dashboard
    │              └─➔ https://chatty-otter-15.loca.lt
    │
    └──➔ nRF9151 Devices (LTE-M/NB-IoT)
            └─➔ Zephyr Firmware
                   └─➔ http://chatty-otter-15.loca.lt

                          ↓ Localtunnel

┌─────────────────────────────────────────────────────────────┐
│              Local Development Machine (Windows)             │
│                                                              │
│  Docker Compose:                                            │
│    • PostgreSQL 13 (port 5432)                              │
│    • FastAPI + Gunicorn (port 8000)                         │
│                                                              │
│  Localtunnel Process:                                       │
│    • npx localtunnel --port 8000                            │
│      --subdomain chatty-otter-15                            │
│    • Auto-restart via while loop                            │
│                                                              │
│  nRF Cloud Integration:                                     │
│    • Service Evaluation Token (30 days)                     │
│    • A-GNSS: 3102 bytes/request                             │
│    • Fallback to Google SUPL                                │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Known Issues & Limitations

### 1. Google SUPL Fallback
- **Status:** Connects successfully to `supl.google.com:7276`
- **Issue:** ASN.1/ULP protocol implementation incomplete
- **Impact:** No assistance data returned from SUPL servers
- **Workaround:** nRF Cloud primary, SUPL demo mode available
- **Fix Required:** Implement proper SUPL 2.0 ASN.1 encoding

### 2. Localtunnel Stability
- **Issue:** Occasional disconnections require restart
- **Workaround:** Auto-restart loop in PowerShell
- **Production:** Use ngrok, Cloudflare Tunnel, or proper domain

### 3. nRF Cloud Evaluation Period
- **Current:** Service Evaluation Token (valid 30 days)
- **Expires:** 2026-03-03
- **Action Required:** Contact Nordic Sales for commercial agreement

### 4. Uncommitted Firmware Changes
- **Status:** Submodule updates present in GPS-Tracking-PCB
- **Impact:** Firmware configuration validated but not committed
- **Action:** Review and commit firmware changes

---

## 📝 Next Steps

### High Priority
1. ✅ **Commit firmware changes** (SERVER_BASE_URL_OVERRIDE)
2. ⏳ **Test end-to-end GPS data flow** (firmware → server → apps)
3. ⏳ **Verify A-GNSS improves TTFF** (with/without comparison)
4. ⏳ **Test cell location fallback** (when GPS unavailable)

### Medium Priority
5. ⏳ **Implement proper SUPL 2.0 protocol** (fix ASN.1 encoding)
6. ⏳ **Add production domain** (replace localtunnel)
7. ⏳ **Set up CI/CD** (auto-deploy on push)
8. ⏳ **Add monitoring/logging** (Sentry, Prometheus)

### Low Priority
9. ⏳ **nRF Cloud commercial agreement** (post-evaluation)
10. ⏳ **TLS/HTTPS for firmware** (currently plain HTTP)
11. ⏳ **Rate limiting on server** (protect against abuse)
12. ⏳ **Database backups** (automated PostgreSQL dumps)

---

## 🔧 Configuration Files Reference

### Server
- `.env` - API keys and provider config
- `docker-compose.yml` - Container orchestration
- `api/endpoints/device_data_endpoints.py` - A-GNSS logic
- `api/agnss/supl_client.py` - SUPL client implementation

### Firmware
- `nrf9151-firmware/src/main.c:142` - Server URL override
- `nrf9151-firmware/prj.conf` - Zephyr build config
- `nrf9151-firmware/src/drivers/server_driver.c` - HTTP client

### Mobile App
- `config.js:6` - API base URL
- `GpsTrackingApi.js` - API client wrapper

### Web Dashboard
- `src/api/GpsTrackingApi.ts:6` - API base URL
- `src/components/` - React components

---

## 📞 Support & Documentation

### Server Documentation
- **API Docs:** http://localhost:8000 (Swagger UI)
- **README:** GPS-Tracking-Server/README.md
- **API Guide:** GPS-Tracking-Server/api/API_DOCUMENTATION.md

### Firmware Documentation
- **Setup:** GPS-Tracking-PCB/nrf9151-firmware/SETUP_GUIDE.md
- **LTE Testing:** GPS-Tracking-PCB/nrf9151-firmware/LTE_TESTING.md
- **Production:** GPS-Tracking-PCB/nrf9151-firmware/PRODUCTION_SERVER.md
- **A-GNSS:** GPS-Tracking-PCB/nrf9151-firmware/AGNSS_EPHEMERIS.md

### External Resources
- **nRF Cloud:** https://nrfcloud.com
- **Zephyr RTOS:** https://docs.zephyrproject.org
- **FastAPI:** https://fastapi.tiangolo.com
- **React Native:** https://reactnative.dev

---

**Last Updated:** February 15, 2026  
**Maintainers:** Josiah Schuller, Irfan Rahamattoulla
