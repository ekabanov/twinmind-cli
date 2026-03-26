"""Firebase authentication for Twinmind via Google sign-in."""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

FIREBASE_API_KEY = "AIzaSyD2Sd_NP3vA4rwvoroKqDefpXZeCMDXcIQ"
FIREBASE_TENANT_ID = "PRODTwinMind-dcnoy"
TOKEN_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
AUTH_FILE = Path.home() / ".twinmind-cli" / "auth.json"
ENV_VAR_NAME = "TWINMIND_REFRESH_TOKEN"

EXTRACT_SNIPPET_FILE = Path(__file__).parent.parent.parent / "extract-token.js"


def _save_tokens(id_token: str, refresh_token: str, expires_in: int = 3600) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id_token": id_token,
        "refresh_token": refresh_token,
        "token_expiry": int(time.time()) + expires_in,
    }
    AUTH_FILE.write_text(json.dumps(data, indent=2))
    logger.info("Tokens saved to %s", AUTH_FILE)


def _load_tokens() -> dict | None:
    if not AUTH_FILE.exists():
        return None
    try:
        return json.loads(AUTH_FILE.read_text())
    except (json.JSONDecodeError, KeyError):
        return None


def refresh_id_token(refresh_token: str) -> tuple[str, str]:
    """Use a refresh token to get a new ID token from Firebase.

    Returns (id_token, refresh_token).
    """
    resp = requests.post(
        TOKEN_REFRESH_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    new_id_token = data["id_token"]
    new_refresh_token = data["refresh_token"]
    expires_in = int(data.get("expires_in", 3600))
    _save_tokens(new_id_token, new_refresh_token, expires_in)
    return new_id_token, new_refresh_token


def get_id_token() -> str:
    """Get a valid Firebase ID token.

    Priority: TWINMIND_REFRESH_TOKEN env var > auth.json file.
    Auto-refreshes expired tokens.

    Raises RuntimeError if no tokens are available.
    """
    # 1. Check environment variable
    env_token = os.environ.get(ENV_VAR_NAME)
    if env_token:
        logger.info("Using refresh token from %s env var", ENV_VAR_NAME)
        id_token, _ = refresh_id_token(env_token.strip())
        return id_token

    # 2. Check auth file
    tokens = _load_tokens()
    if tokens is None:
        raise RuntimeError(
            "No auth tokens found. Run 'twinmind auth' or set TWINMIND_REFRESH_TOKEN."
        )

    # Refresh if token expires within 5 minutes
    if time.time() > tokens["token_expiry"] - 300:
        logger.info("Token expired or expiring soon, refreshing...")
        try:
            id_token, _ = refresh_id_token(tokens["refresh_token"])
            return id_token
        except requests.HTTPError as e:
            raise RuntimeError(
                f"Token refresh failed ({e}). Run 'twinmind auth' to re-authenticate."
            ) from e

    return tokens["id_token"]


def browser_auth() -> str:
    """Guide the user to extract their Firebase refresh token from the browser.

    Returns the ID token.
    """
    # Copy the JS snippet to clipboard for easy pasting
    snippet_copied = False
    if EXTRACT_SNIPPET_FILE.exists():
        snippet = EXTRACT_SNIPPET_FILE.read_text().strip()
        try:
            subprocess.run(
                ["pbcopy"], input=snippet.encode(), check=True, timeout=5
            )
            snippet_copied = True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    print("=" * 60)
    print("TWINMIND AUTHENTICATION")
    print("=" * 60)
    print()
    print("1. Open https://app.twinmind.com in Chrome and sign in")
    print()
    print("2. Open Chrome DevTools Console (Cmd+Option+J)")
    print()
    if snippet_copied:
        print("3. The extraction script is already in your clipboard!")
        print("   Just paste (Cmd+V) in the console and press Enter.")
    else:
        print("3. Copy the contents of extract-token.js and paste in console:")
        print(f"   {EXTRACT_SNIPPET_FILE}")
    print()
    print("4. The refresh token will be copied to your clipboard.")
    print("   Paste it below (Cmd+V):")
    print()

    refresh_token = input("Refresh token: ").strip()

    if not refresh_token:
        raise RuntimeError("No token provided.")

    # Clean up common copy artifacts from browser console
    if (refresh_token.startswith('"') and refresh_token.endswith('"')) or \
       (refresh_token.startswith("'") and refresh_token.endswith("'")):
        refresh_token = refresh_token[1:-1]
    refresh_token = refresh_token.lstrip("> ").strip()

    # Exchange refresh token for id_token
    print("\nExchanging token...")
    try:
        id_token, _ = refresh_id_token(refresh_token)
    except requests.HTTPError as e:
        raise RuntimeError(f"Token exchange failed: {e}") from e

    # Verify the token works
    print("Verifying token...")
    try:
        resp = requests.post(
            "https://api.thirdear.live/api/v1/get_memory_titles",
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=30,
        )
        resp.raise_for_status()
        print("\nAuthentication successful! Tokens saved.")
        return id_token
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            raise RuntimeError(
                "Token verification failed - the token may be invalid. "
                "Make sure you're signed in and try again."
            ) from e
        print("\nAuthentication saved (could not verify - API may be temporarily unavailable).")
        return id_token
