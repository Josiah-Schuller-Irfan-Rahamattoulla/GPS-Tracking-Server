import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2

from endpoints import app_user_endpoints, device_data_endpoints, cell_location, realtime_endpoints
from endpoints.authorisation import authorise_device, authorise_user

# Load .env from api/ dir then project root (so it works from any cwd)
_api_dir = os.path.abspath(os.path.dirname(__file__))
_root_dir = os.path.abspath(os.path.join(_api_dir, ".."))
for _d in (_api_dir, _root_dir):
    _env = os.path.join(_d, ".env")
    if os.path.isfile(_env):
        load_dotenv(_env)

app = FastAPI(
    title="GPS Tracking Server API",
    version="0.1.0",
    docs_url="/",
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple liveness check plus a quick database connectivity test.

    The API will attempt to open (and immediately close) a connection using
    ``DATABASE_URI``.  This helps ensure that a Supabase/PostgreSQL instance
    referenced by the environment is reachable.  If the connection fails the
    endpoint **does not** return HTTP 200; instead a 503 Service Unavailable
    error is raised so that orchestrators can mark the container unhealthy.

    The JSON payload still includes ``status`` and, when
    ``DATABASE_URI`` is set, a ``database`` field indicating the result or
    error message.
    """
    result = {"status": "healthy"}

    dsn = os.getenv("DATABASE_URI")
    try:
        conn = psycopg2.connect(dsn=dsn)
        conn.close()
        result["database"] = "healthy"
    except Exception as ex:  # pragma: no cover - network/database errors
        # show error details for debugging
        msg = f"unhealthy: {str(ex)}"
        result["database"] = msg
        # if the database is unreachable, raise an HTTPException so the
        # status code is 503 instead of 200
        raise HTTPException(status_code=503, detail=result)
    return result

# CORS: use CORS_ORIGINS in production (comma-separated). Empty or unset = allow all (dev).
_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(
    router=device_data_endpoints.router,
    prefix="/v1",
    dependencies=[Depends(authorise_device)],
    tags=["Endpoints for PCB device to call"],
)
app.include_router(
    router=device_data_endpoints.device_registration_router,
    prefix="/v1",
    tags=["PCB device registration endpoints"],
)
app.include_router(
    router=app_user_endpoints.router,
    prefix="/v1",
    dependencies=[Depends(authorise_user)],
    tags=["Endpoints for app users to call"],
)
app.include_router(
    router=app_user_endpoints.auth_router,
    prefix="/v1",
    tags=["App authentication endpoints"],
)
app.include_router(
    router=cell_location.router,
    prefix="/v1",
    dependencies=[Depends(authorise_device)],
    tags=["Cell-based location services"],
)
# WebSocket routes (no HTTP auth; token in query string)
app.include_router(
    router=realtime_endpoints.router,
    prefix="/v1",
    tags=["WebSocket real-time streaming"],
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
