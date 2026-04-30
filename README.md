# GPS-Tracking-Server

A FastAPI-based GPS tracking server with PostgreSQL database support for managing devices, users, and GPS location data.

## Features

✅ **Core Functionality**
- Device registration and management
- GPS data storage and retrieval
- User authentication (opaque access tokens)
- Geofence CRUD operations
- Trip tracking (start/end detection)
- Multi-device support per user
- A-GNSS proxy for nRF Cloud

✅ **Advanced Features**
- **Server-side geofence breach detection** - Automatic monitoring of all devices
- **Email notifications** - SMTP-based alerts for geofence breaches
- **SMS notifications** - Twilio or AWS SNS integration for instant alerts
- **Geofence breach event logging** - Complete audit trail with timestamps

📋 **Planned Features** (see [FIRMWARE_INTEGRATION_PLAN.md](FIRMWARE_INTEGRATION_PLAN.md))
- A-GNSS integration in firmware (5-10x faster GPS acquisition)
- Offline GPS buffering (prevent data loss)
- Adaptive upload frequency (power savings)
- WebSocket support (real-time updates)

## Local Set-Up Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL database
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GPS-Tracking-Server
   ```

2. **Install uv** (if not already installed)
   ```bash
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # On Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Navigate to the API directory**
   ```bash
   cd api
   ```

4. Create virtual environment
   ```bash
   uv venv
   . .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   # Install production dependencies
   uv pip sync requirements.txt
   
   # Or install with development dependencies
   uv pip sync requirements-dev.txt
   ```

5. **Set up environment variables**
   Create a `.env` file in the `api` directory (see `.env.example`). Required:
   ```
   DATABASE_URI=postgresql://username:password@server:5432/database_name
   ```

6. **Set up the database (OPTIONAL)**
   - Create a PostgreSQL database
   - Run the SQL schema from `database/gps_tracking_database.sql`, then migrations in `database/migration_001_*` through `migration_009_*` in order.
   - For device-in-vehicle flow and production readiness, see [docs/DEVICE_AND_PRODUCTION_READINESS.md](docs/DEVICE_AND_PRODUCTION_READINESS.md).

### Running the Application

```bash
python main.py
```

The server will start on `http://localhost:8000` with interactive API documentation available at the root URL.

## API Endpoints

- **GET /** - Interactive API documentation (Swagger UI). You can see all other endpoints documented here.

## Notification System

The server supports automatic notifications for geofence breach events. When a device crosses a geofence boundary, the system can send notifications via:

### Email Notifications (SMTP)

Configure email notifications by setting these environment variables:

```bash
NOTIFY_GEOFENCE_EMAIL=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM="GPS Tracker <your-email@gmail.com>"
```

**Gmail Setup:**
1. Enable 2-factor authentication on your Gmail account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in `SMTP_PASSWORD`

### SMS Notifications

Choose one SMS provider:

#### Option 1: Twilio

```bash
NOTIFY_GEOFENCE_SMS_TWILIO=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_PHONE=+1234567890
```

Install Twilio SDK:
```bash
pip install twilio
```

#### Option 2: AWS SNS

```bash
NOTIFY_GEOFENCE_SMS_AWS=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

Install AWS SDK:
```bash
pip install boto3
```

### How It Works

1. Device sends GPS coordinates to `/sendGPSData`
2. Server checks all geofences for all users with access to the device
3. If a breach is detected (ENTERED or EXITED), the server:
   - Logs the event in `geofence_breach_events` table
   - Sends email notification (if enabled)
   - Sends SMS notification (if enabled)
   - Marks the event as notified

**Note:** SMS is sent to the `sms_number` field stored in the `devices` table during device registration.

## Development

### Code Quality

```bash
# Run linting and formatting
ruff check .
ruff format .
```

### Updating Dependencies

```bash
# Update requirements.txt
uv pip compile --output-file requirements.txt pyproject.toml

# Update dev requirements
uv pip compile --output-file requirements-dev.txt --extra dev pyproject.toml
```

