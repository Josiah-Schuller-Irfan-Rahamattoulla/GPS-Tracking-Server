# Quick Start Guide - Server Setup

## Prerequisites
- PostgreSQL database running
- Python 3.8+
- Docker (optional, for containerized setup)

## Step 1: Run Database Migration

```bash
# Connect to PostgreSQL and run migration
psql -U your_username -d your_database_name -f database/migration_001_add_features.sql
```

**Or manually in psql:**
```sql
\i database/migration_001_add_features.sql
```

## Step 2: Configure Environment

Create `api/.env`:
```env
DATABASE_URI=postgresql://username:password@localhost:5432/database_name
```

## Step 3: Install Dependencies

```bash
cd api
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip sync requirements.txt
```

## Step 4: Start Server

```bash
python main.py
```

Server starts on `http://localhost:8000`

## Step 5: Test

```bash
# Install requests if needed
pip install requests

# Run test script
python test_new_endpoints.py --base-url http://localhost:8000
```

## What Was Added

✅ GPS data now stores: speed, heading, trip_active  
✅ Devices can have names  
✅ Device controls can be updated remotely  
✅ Trip status endpoint for hardware IMU detection  
✅ Complete geofence management system  
✅ Optimistic locking for concurrent control updates  

## API Documentation

Visit `http://localhost:8000` in browser for interactive Swagger UI documentation.

## Troubleshooting

**Migration fails:**
- Check PostgreSQL version (9.5+)
- Verify user has ALTER TABLE permissions
- Check for existing columns (migration uses IF NOT EXISTS)

**Server won't start:**
- Check DATABASE_URI in .env
- Verify PostgreSQL is running
- Check Python version (3.8+)

**Tests fail:**
- Ensure server is running
- Check database migration completed
- Verify DATABASE_URI is correct

