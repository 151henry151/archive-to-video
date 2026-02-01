"""
YouTube OAuth 2.0 web flow for multi-user web app.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def get_flow(redirect_uri: str, credentials_path: str = "config/client_secrets.json") -> Flow:
    """
    Create Flow for web OAuth.

    The client_secrets.json must be for a "Web application" OAuth client
    in Google Cloud Console, with redirect_uri in authorized redirect URIs.
    """
    path = Path(credentials_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Credentials not found at {credentials_path}. "
            "Create a Web application OAuth client in Google Cloud Console."
        )

    # Flow.from_client_secrets_file uses redirect_uri from kwargs
    flow = Flow.from_client_secrets_file(
        str(path),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


def get_authorization_url(redirect_uri: str, state: Optional[str] = None) -> Tuple[str, str]:
    """
    Get YouTube OAuth authorization URL for user to visit.

    Returns:
        (authorization_url, state)
    """
    flow = get_flow(redirect_uri)
    url, flow_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state or "",
    )
    return url, flow_state


def exchange_code_for_credentials(
    code: str, redirect_uri: str, credentials_path: str = "config/client_secrets.json"
) -> Credentials:
    """
    Exchange authorization code for Credentials.
    """
    flow = get_flow(redirect_uri, credentials_path)
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_to_dict(creds: Credentials) -> dict:
    """Serialize Credentials for session storage."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else list(SCOPES),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def dict_to_credentials(data: dict) -> Credentials:
    """Deserialize Credentials from session storage."""
    expiry = data.get("expiry")
    if expiry and isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES),
        expiry=expiry,
    )
