"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, projects, webhooks, characters

app = FastAPI(title="VoiceCheck API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(characters.router)
app.include_router(webhooks.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
