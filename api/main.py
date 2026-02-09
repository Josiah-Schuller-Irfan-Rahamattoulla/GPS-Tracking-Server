import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from endpoints import app_user_endpoints, device_data_endpoints, cell_location
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
    return {"status": "healthy"}

# Enable CORS (useful for frontend-backend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: not a great security practice. Change in production!
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
