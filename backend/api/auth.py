"""
YouTube OAuth auth API.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

from backend.utils import get_base_url
from backend.services.youtube_web_auth import (
    get_authorization_url,
    exchange_code_for_credentials,
    credentials_to_dict,
    dict_to_credentials,
)

router = APIRouter()


@router.get("/auth/status")
def auth_status(request: Request):
    """Check if user has valid YouTube credentials in session."""
    session = request.session
    creds_data = session.get("youtube_credentials")
    if not creds_data:
        return {"authenticated": False}
    try:
        creds = dict_to_credentials(creds_data)
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            session["youtube_credentials"] = credentials_to_dict(creds)
        return {"authenticated": creds.valid}
    except Exception:
        return {"authenticated": False}


@router.get("/auth/youtube/url")
def get_youtube_auth_url(request: Request):
    """Get YouTube OAuth URL for user to redirect to."""
    base_url = get_base_url(request)
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/youtube/callback"
    try:
        url, state = get_authorization_url(redirect_uri)
        request.session["oauth_state"] = state
        return {"url": url}
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/youtube/callback")
def youtube_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """OAuth callback - exchange code for credentials, store in session."""
    if error:
        # User denied or error - redirect to frontend with error
        return RedirectResponse(url="/?error=auth_denied", status_code=302)
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    base_url = get_base_url(request)
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/youtube/callback"

    try:
        creds = exchange_code_for_credentials(code, redirect_uri)
        request.session["youtube_credentials"] = credentials_to_dict(creds)
        # Redirect to frontend (landing) - user is now signed in
        return RedirectResponse(url="/?signed_in=1", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)[:100]}", status_code=302)


@router.post("/auth/logout")
def logout(request: Request):
    """Clear YouTube credentials from session."""
    request.session.pop("youtube_credentials", None)
    request.session.pop("oauth_state", None)
    return {"ok": True}


def get_session_credentials(request: Request):
    """Get Credentials from session if authenticated."""
    creds_data = request.session.get("youtube_credentials")
    if not creds_data:
        return None
    try:
        creds = dict_to_credentials(creds_data)
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            request.session["youtube_credentials"] = credentials_to_dict(creds)
        return creds if creds.valid else None
    except Exception:
        return None
