"""
Main FastAPI application.
Authentication + API Key Service for service-to-service and user authentication.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base
from app.routers import auth, api_keys, protected, wallet


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
    title="Wallet Service API",
    description="""
    Backend wallet service with Paystack integration, JWT authentication, and API key management.
    
    ## Authentication Methods
    
    ### 1. JWT Bearer Token
    - Obtain via `/auth/login` or `/auth/signup` or `/auth/google/callback`
    - Use in Swagger: Click **Authorize** → Enter token in **BearerAuth** field
    - Format: `Authorization: Bearer <your_jwt_token>`
    
    ### 2. API Key
    - Create via `/keys/create` (requires JWT first)
    - Use in Swagger: Click **Authorize** → Enter key in **ApiKeyAuth** field
    - Format: `x-api-key: <your_api_key>`
    
    **Note**: Some endpoints accept EITHER JWT OR API key (with proper permissions).
    """,
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add session middleware FIRST (middleware applied in reverse order)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    max_age=3600,
    same_site="lax",
    https_only=False,
)

# Configure CORS AFTER session middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure OpenAPI security schemes for Swagger UI
app.openapi_schema = None  # Reset to regenerate with security

from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from login/signup",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "Enter your API key (create via /keys/create)",
        },
    }

    # Apply security to all paths except public ones
    public_paths = [
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/auth/google",
        "/auth/google/callback",
        "/auth/signup",
        "/auth/login",
    ]

    for path, path_item in openapi_schema.get("paths", {}).items():
        # Skip public endpoints
        if path in public_paths:
            continue

        # Apply security to all methods in this path
        for method in path_item:
            if method in ["get", "post", "put", "delete", "patch"]:
                # Add both auth methods as alternatives (user can use either)
                path_item[method]["security"] = [{"BearerAuth": []}, {"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Include routers
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(wallet.router)
app.include_router(protected.router)


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information and available endpoints.
    """
    return {
        "message": "Wallet Service with Paystack, JWT & API Keys",
        "version": "2.0.0",
        "documentation": "/docs",
        "endpoints": {
            "authentication": {
                "signup": "POST /auth/signup",
                "login": "POST /auth/login",
                "google_oauth": "GET /auth/google",
            },
            "api_keys": {
                "create": "POST /keys/create",
                "list": "GET /keys",
                "rollover": "POST /keys/rollover",
                "revoke": "DELETE /keys/{key_id}",
            },
            "wallet": {
                "balance": "GET /wallet/balance",
                "deposit": "POST /wallet/deposit",
                "transfer": "POST /wallet/transfer",
                "transactions": "GET /wallet/transactions",
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
    return {"status": "healthy", "service": "Wallet Service with Paystack & API Keys"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
