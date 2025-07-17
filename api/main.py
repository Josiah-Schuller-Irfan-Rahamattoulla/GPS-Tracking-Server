import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from endpoints import device_data_endpoint

# from app.api.v1.endpoints import users, items  # example endpoints

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
# TODO add authorization
app.include_router(
    router=device_data_endpoint.router,
    prefix="/v1",
    tags=["Endpoints for PCB device to call"],
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
