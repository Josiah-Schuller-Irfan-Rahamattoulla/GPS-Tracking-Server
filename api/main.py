import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from endpoints import app_user_endpoints, device_data_endpoints
from endpoints.authorisation import authorise_device, authorise_user

load_dotenv()  # Load environment variables from .env file

app = FastAPI(
    title="GPS Tracking Server API",
    version="0.1.0",
    docs_url="/",
)

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
    router=app_user_endpoints.router,
    prefix="/v1",
    dependencies=[Depends(authorise_user)],
    tags=["Endpoints for app users to call"],
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
