"""
Famous Media Technologies — Official Discord OAuth2 Engine
Handles secure, compliant authorization code flow directly with Discord's official OAuth2 API.
Zero self-bots, zero personal account token scraping.
"""

import os
import asyncio
import secrets
import urllib.parse
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from app.database import (
    get_connection, save_discord_oauth, get_discord_oauth,
    delete_discord_oauth, save_user_guilds, get_user_guilds,
    get_bot_setting, set_bot_setting
)

logger = logging.getLogger("famous.discord_oauth")

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
OAUTH_SCOPES = ["identify", "guilds"]

def is_valid_discord_snowflake(val: Optional[str]) -> bool:
    """
    Validates if a string is a legitimate Discord snowflake ID.
    Discord snowflakes are 17-20 digit integers.
    Rejects mock IDs and placeholders.
    """
    if not val:
        return False
    s = str(val).strip()
    if not s.isdigit() or len(s) < 17 or len(s) > 20:
        return False
    # Reject common development placeholders
    if s.startswith("1234567890") or s == "0" * len(s) or s == "1" * len(s):
        return False
    return True

def is_valid_client_secret(val: Optional[str]) -> bool:
    """
    Validates if a string is a non-empty, non-mock Discord Client Secret.
    """
    if not val:
        return False
    s = str(val).strip()
    if len(s) < 16:
        return False
    if s.lower() in [
        "mock_client_secret_xyz",
        "enter-client-secret",
        "your_client_secret",
        "placeholder",
        "client_secret_here"
    ]:
        return False
    return True

def get_oauth_config() -> Dict[str, Any]:
    """
    Retrieves OAuth2 configuration with strict validation and security masking.
    Checks environment variables (.env) and local database settings.
    """
    db_cid = (get_bot_setting("discord_client_id") or "").strip()
    env_cid = os.getenv("DISCORD_CLIENT_ID", "").strip()
    client_id = db_cid if db_cid else env_cid

    db_secret = (get_bot_setting("discord_client_secret") or "").strip()
    env_secret = os.getenv("DISCORD_CLIENT_SECRET", "").strip()
    client_secret = db_secret if db_secret else env_secret

    db_ruri = (get_bot_setting("discord_redirect_uri") or "").strip()
    env_ruri = os.getenv("DISCORD_REDIRECT_URI", "").strip()
    redirect_uri = db_ruri or env_ruri or "http://127.0.0.1:8080/api/auth/discord/callback"

    valid_id = is_valid_discord_snowflake(client_id)
    valid_secret = is_valid_client_secret(client_secret)
    is_configured = valid_id and valid_secret

    # Mask client secret for security
    masked_secret = ""
    if client_secret:
        if len(client_secret) > 8:
            masked_secret = client_secret[:4] + "••••••••" + client_secret[-4:]
        else:
            masked_secret = "••••••••"

    status_message = "Configured and ready"
    if not client_id and not client_secret:
        status_message = "Credentials not configured. Please enter your Discord Application Client ID and Client Secret."
    elif not valid_id:
        status_message = "Invalid Client ID. Discord Application Client ID must be a 17-20 digit numeric snowflake from Discord Developer Portal."
    elif not valid_secret:
        status_message = "Invalid Client Secret. Enter your 32-character Client Secret from Discord Developer Portal (OAuth2 > General)."

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_secret_masked": masked_secret,
        "redirect_uri": redirect_uri,
        "is_configured": is_configured,
        "is_client_id_valid": valid_id,
        "is_client_secret_valid": valid_secret,
        "status_message": status_message
    }

def set_oauth_config(client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8080/api/auth/discord/callback") -> Dict[str, Any]:
    """
    Saves and validates Discord OAuth2 credentials into database settings.
    """
    cid = client_id.strip()
    csecret = client_secret.strip()
    ruri = (redirect_uri or "http://127.0.0.1:8080/api/auth/discord/callback").strip()

    set_bot_setting("discord_client_id", cid)
    set_bot_setting("discord_client_secret", csecret)
    set_bot_setting("discord_redirect_uri", ruri)

    return get_oauth_config()

def generate_authorization_url(redirect_uri: Optional[str] = None) -> Tuple[str, str]:
    """
    Generates official Discord OAuth2 authorization URL with anti-CSRF state token.
    Raises ValueError with descriptive instructions if credentials are invalid or missing.
    """
    config = get_oauth_config()
    if not config["is_configured"]:
        raise ValueError(config["status_message"])

    state = secrets.token_urlsafe(24)
    # Store CSRF state in database with expiration
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO auth_config (key, value, updated_at)
    VALUES ('oauth_csrf_state', ?, CURRENT_TIMESTAMP)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (state,))
    conn.commit()
    conn.close()

    effective_ruri = (redirect_uri or config["redirect_uri"]).strip()
    params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "redirect_uri": effective_ruri,
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "prompt": "consent"
    }

    url = f"{DISCORD_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return url, state

def verify_csrf_state(state: str) -> bool:
    """Verifies that the callback state matches our stored anti-CSRF token."""
    if not state:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM auth_config WHERE key = 'oauth_csrf_state'")
    row = cursor.fetchone()
    conn.close()
    if not row or not secrets.compare_digest(row["value"], state):
        return False
    return True

async def exchange_code_for_token(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """Exchanges OAuth2 authorization code for an official Discord Access Token."""
    config = get_oauth_config()
    if not config["is_configured"]:
        raise ValueError("Cannot exchange code: Discord OAuth2 is not configured.")

    token_url = f"{DISCORD_API_BASE}/oauth2/token"
    effective_ruri = (redirect_uri or config["redirect_uri"]).strip()

    payload = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": effective_ruri
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                error_desc = data.get("error_description") or data.get("error") or f"HTTP {resp.status}"
                raise Exception(f"Discord Token Exchange Failed: {error_desc}")
            return data

async def fetch_discord_user_profile(access_token: str) -> Dict[str, Any]:
    """Queries Discord /users/@me with authorized bearer token."""
    url = f"{DISCORD_API_BASE}/users/@me"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch Discord user profile: HTTP {resp.status}")
            return await resp.json()

async def refresh_user_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refreshes an expired Discord OAuth2 access token."""
    config = get_oauth_config()
    if not config["is_configured"]:
        raise ValueError("Cannot refresh token: Discord OAuth2 is not configured.")

    token_url = f"{DISCORD_API_BASE}/oauth2/token"
    payload = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                err_msg = data.get("error_description") or data.get("error") or f"HTTP {resp.status}"
                raise Exception(f"Token refresh failed: {err_msg}")

            # Update stored tokens in DB
            account = get_discord_oauth()
            if account:
                expires_in = data.get("expires_in", 604800)
                expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
                account["access_token"] = data["access_token"]
                account["refresh_token"] = data.get("refresh_token", refresh_token)
                account["expires_at"] = expires_at
                account["scope"] = data.get("scope", account.get("scope", "identify guilds"))
                save_discord_oauth(account)
            return data

async def fetch_discord_user_guilds(access_token: str, auto_refresh: bool = True) -> List[Dict[str, Any]]:
    """
    Queries Discord /users/@me/guilds to retrieve user's authorized servers.
    Handles rate limits, calculates management permissions, and auto-refreshes token if expired.
    """
    url = f"{DISCORD_API_BASE}/users/@me/guilds"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 401 and auto_refresh:
                # Token may have expired, attempt refresh
                account = get_discord_oauth()
                if account and account.get("refresh_token") and not account.get("refresh_token", "").startswith("demo_") and not account.get("refresh_token", "").startswith("manual_"):
                    try:
                        logger.info("Access token expired (401), refreshing token...")
                        refreshed = await refresh_user_access_token(account["refresh_token"])
                        new_token = refreshed["access_token"]
                        return await fetch_discord_user_guilds(new_token, auto_refresh=False)
                    except Exception as e:
                        logger.error(f"Failed to auto-refresh access token: {e}")
                raise Exception("Discord authorization expired or invalid. Please click 'Sign in with Discord' to re-authorize.")

            if resp.status == 429:
                data = await resp.json()
                retry_after = data.get("retry_after", 1)
                logger.warning(f"Discord rate limited on /users/@me/guilds. Retrying in {retry_after}s")
                await asyncio.sleep(float(retry_after))
                return await fetch_discord_user_guilds(access_token, auto_refresh=False)

            if resp.status != 200:
                err_text = await resp.text()
                logger.error(f"Failed to fetch user guilds: HTTP {resp.status} - {err_text}")
                raise Exception(f"Failed to fetch Discord servers: HTTP {resp.status}")

            raw_guilds = await resp.json()

    processed_guilds = []
    for g in raw_guilds:
        gid = str(g.get("id"))
        icon_hash = g.get("icon")
        icon_url = f"https://cdn.discordapp.com/icons/{gid}/{icon_hash}.webp?size=128" if icon_hash else "https://cdn.discordapp.com/embed/avatars/0.png"

        is_owner = bool(g.get("owner", False))
        permissions_raw = str(g.get("permissions", "0"))
        try:
            permissions_int = int(permissions_raw)
        except (ValueError, TypeError):
            permissions_int = 0

        # Permissions to add a bot: Administrator (0x8) or Manage Server / Manage Guild (0x20) or Owner
        can_manage = is_owner or bool(permissions_int & 0x8) or bool(permissions_int & 0x20)
        role_badge = "Server Owner" if is_owner else ("Administrator" if (permissions_int & 0x8) else ("Manager" if (permissions_int & 0x20) else "Member"))

        processed_guilds.append({
            "id": gid,
            "guild_id": gid,
            "name": g.get("name", "Unknown Server"),
            "icon": icon_hash or "",
            "icon_url": icon_url,
            "owner": is_owner,
            "permissions": permissions_raw,
            "permissions_int": permissions_int,
            "can_manage": can_manage,
            "role_badge": role_badge
        })

    return processed_guilds

async def revoke_discord_token(token: str) -> bool:
    """Revokes OAuth2 token with Discord API."""
    config = get_oauth_config()
    if not config["is_configured"]:
        return True

    url = f"{DISCORD_API_BASE}/oauth2/token/revoke"
    payload = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "token": token
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as resp:
                return resp.status == 200
    except Exception as e:
        logger.warning(f"Error revoking Discord token: {e}")
        return False
