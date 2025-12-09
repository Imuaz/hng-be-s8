"""
Google OAuth service for user authentication.
"""

from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.config import settings

# OAuth configuration
config = Config(
    environ={
        "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
    }
)

oauth = OAuth(config)

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
