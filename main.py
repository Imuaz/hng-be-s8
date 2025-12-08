"""
Main FastAPI application.
Authentication + API Key Service for service-to-service and user authentication.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base
from app.routers import auth, api_keys, protected


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the application.
    Creates database tables on startup (except during testing).
    """
    # Startup: Create database tables only if not in test mode
    import os

    if not os.getenv("TESTING"):
        Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


# Create FastAPI application
app = FastAPI(
    title="Authentication + API Key Service",
    description="Task 3: Mini Authentication + API Key System for Service-to-Service Access",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(protected.router)


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information and available endpoints.
    """
    return {
        "message": "Authentication + API Key Service",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "authentication": {
                "signup": "POST /auth/signup",
                "login": "POST /auth/login",
            },
            "api_keys": {
                "create": "POST /keys/create",
                "list": "GET /keys",
                "revoke": "DELETE /keys/{key_id}",
            },
            "protected_demos": {
                "user_only": "GET /protected/user (JWT only)",
                "service_only": "GET /protected/service (API key only)",
                "any_auth": "GET /protected/any (JWT or API key)",
            },
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "service": "Authentication + API Key Service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
