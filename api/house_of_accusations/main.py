from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from house_of_accusations.config import get_settings
from house_of_accusations.sessions import router as sessions_router

app = FastAPI(title="House of Accusations API", version="0.1.0")

_settings = get_settings()
_allowed_origins = _settings.allowed_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(sessions_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
