"""
Famous Media Technologies — Discord OAuth2 Automated Verification Suite
Direct asynchronous endpoint and validation testing without anyio/testclient blocking.
"""

import sys
import os
import asyncio
from pathlib import Path
from starlette.requests import Request
from starlette.datastructures import Headers

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.discord_oauth import (
    is_valid_discord_snowflake, is_valid_client_secret,
    get_oauth_config, set_oauth_config, generate_authorization_url,
    verify_csrf_state
)
from app.database import set_bot_setting
from app.main import (
    api_discord_oauth_login,
    api_discord_oauth_get_config,
    api_discord_oauth_set_config,
    api_discord_oauth_status,
    OAuthConfigPayload
)
from fastapi import HTTPException

def make_dummy_request(path: str = "/api/auth/discord/login", query_string: bytes = b"") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "server": ("127.0.0.1", 8080),
        "headers": [(b"host", b"127.0.0.1:8080")],
        "path": path,
        "query_string": query_string,
    }
    return Request(scope)

async def run_all_tests():
    print("=" * 60)
    print("DISCORD OAUTH2 AUTOMATED VERIFICATION SUITE")
    print("=" * 60)

    # 1. Snowflake validation
    print("\n[1/5] Testing Discord Snowflake Validation...")
    assert is_valid_discord_snowflake("982314589211048999") is True
    assert is_valid_discord_snowflake("134123456789012345") is True
    assert is_valid_discord_snowflake("13412345678901234567") is True
    assert is_valid_discord_snowflake("") is False
    assert is_valid_discord_snowflake(None) is False
    assert is_valid_discord_snowflake("not_numeric") is False
    assert is_valid_discord_snowflake("12345") is False
    assert is_valid_discord_snowflake("123456789012345678") is False # Dummy placeholder sequence
    assert is_valid_discord_snowflake("000000000000000000") is False
    print("  -> Snowflake validation PASS (Rejects mock 123456789012345678).")

    # 2. Secret validation
    print("\n[2/5] Testing Client Secret Validation...")
    assert is_valid_client_secret("secret_abcdef1234567890_test_secr") is True
    assert is_valid_client_secret("") is False
    assert is_valid_client_secret(None) is False
    assert is_valid_client_secret("short") is False
    assert is_valid_client_secret("mock_client_secret_xyz") is False
    print("  -> Client Secret validation PASS (Rejects mock_client_secret_xyz).")

    # 3. Unconfigured behavior & Safe Redirection
    print("\n[3/5] Testing Unconfigured State Redirection...")
    set_bot_setting("discord_client_id", "")
    set_bot_setting("discord_client_secret", "")

    cfg = get_oauth_config()
    assert cfg["is_configured"] is False
    assert "not configured" in cfg["status_message"].lower()

    # Calling login endpoint when unconfigured should redirect back with error parameter
    req = make_dummy_request("/api/auth/discord/login")
    login_resp = await api_discord_oauth_login(req)
    assert login_resp.status_code == 303
    target_url = login_resp.headers.get("location", "")
    assert "/?discord_error=" in target_url
    assert "#discord" in target_url
    print(f"  -> Safe Redirection PASS: {target_url}")

    # 4. Canonical URL generation with Valid Credentials
    print("\n[4/5] Testing Canonical OAuth2 URL & Anti-CSRF...")
    valid_test_cid = "982314589211048999"
    valid_test_secret = "secret_valid_client_key_32_characters_123"
    set_oauth_config(valid_test_cid, valid_test_secret, "http://127.0.0.1:8080/api/auth/discord/callback")

    cfg = get_oauth_config()
    assert cfg["is_configured"] is True
    assert "••••••••" in cfg["client_secret_masked"]
    assert valid_test_secret not in cfg["client_secret_masked"]

    login_resp2 = await api_discord_oauth_login(req)
    assert login_resp2.status_code == 303
    oauth_url = login_resp2.headers.get("location", "")
    assert oauth_url.startswith("https://discord.com/oauth2/authorize?")
    assert f"client_id={valid_test_cid}" in oauth_url
    assert "response_type=code" in oauth_url
    assert "scope=identify+guilds" in oauth_url
    assert "state=" in oauth_url
    print(f"  -> Canonical URL PASS: {oauth_url[:80]}...")

    # 5. REST API Endpoints (GET and POST config, and status)
    print("\n[5/5] Testing Config Endpoints & Input Protection...")
    # GET config
    cfg_resp = await api_discord_oauth_get_config(req)
    import json
    cfg_data = json.loads(cfg_resp.body.decode())
    assert cfg_data["client_id"] == valid_test_cid
    assert cfg_data["is_configured"] is True
    assert cfg_data["suggested_redirect_uri"] == "http://127.0.0.1:8080/api/auth/discord/callback"

    # POST config with dummy snowflake 123456789012345678 -> Should raise HTTPException 400
    try:
        await api_discord_oauth_set_config(
            OAuthConfigPayload(
                client_id="123456789012345678",
                client_secret="secret_valid_client_key_32_characters_123"
            ),
            req
        )
        assert False, "Should have rejected dummy sequence 123456789012345678"
    except HTTPException as e:
        assert e.status_code == 400
        assert "Invalid Client ID" in e.detail
        print("  -> Successfully blocked dummy Client ID '123456789012345678' with HTTP 400.")

    # Status check
    status_resp = await api_discord_oauth_status(req)
    status_data = json.loads(status_resp.body.decode())
    assert status_data["oauth_configured"] is True
    assert status_data["client_id"] == valid_test_cid

    print("  -> REST endpoints PASS.")

    print("\n" + "=" * 60)
    print("ALL DISCORD OAUTH2 TESTS COMPLETED SUCCESSFULLY (100% PASS)")
    print("=" * 60)

def cleanup():
    set_bot_setting("discord_client_id", "")
    set_bot_setting("discord_client_secret", "")
    print("\n[CLEANUP] Database reset to clean unconfigured state for user.")

if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    finally:
        cleanup()
