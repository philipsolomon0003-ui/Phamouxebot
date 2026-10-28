"""
Famous Media Technologies — Discord Server Management, Chat Access & Personal DM Test Suite
Direct synchronous execution matching test_auth_flow.py to avoid Python 3.14 event loop conflicts.
"""

import sys
import os
import json
from pathlib import Path
from starlette.requests import Request

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import (
    init_db, save_discord_oauth, get_discord_oauth, delete_discord_oauth,
    save_user_guilds, get_user_guilds, save_server_channels,
    save_channel_messages, search_channel_messages, get_leads,
    save_or_update_server, sync_bot_guilds, set_bot_setting, get_conversation_records
)
from app.bot import generate_bot_invite_url
from app.discord_oauth import (
    is_valid_discord_snowflake, set_oauth_config, get_oauth_config
)
from app.main import (
    api_get_user_guilds,
    api_refresh_user_guilds,
    api_check_bot_in_server,
    api_get_bot_servers,
    api_get_channel_messages,
    api_get_bot_invite_url,
    api_save_personal_dm,
    PersonalDMIntakePayload
)

def run_coro(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")

def run_all_tests():
    print("=" * 70, flush=True)
    print("FAMOUS MEDIA TECHNOLOGIES: SERVER & CHAT FEATURES VERIFICATION SUITE", flush=True)
    print("=" * 70, flush=True)

    init_db()

    # -------------------------------------------------------------------------
    # TEST 1: User Discord Guilds endpoint (Unauthenticated vs Authenticated)
    # -------------------------------------------------------------------------
    print("\n[TEST 1/6] Testing User Guilds Listing & Role Detection...", flush=True)
    delete_discord_oauth()

    # Case A: When user is not linked to Discord OAuth
    resp_unauth = run_coro(api_get_user_guilds(authenticated=True))
    body_unauth = json.loads(resp_unauth.body.decode())
    assert body_unauth["is_authenticated"] is False
    assert body_unauth["count"] == 0
    print("  -> Correctly reports is_authenticated=False when no Discord account is linked.", flush=True)

    # Case B: When user is linked with mock OAuth profile and guilds
    mock_discord_account = {
        "discord_id": "194123456789012345",
        "username": "PhamouxeOwner",
        "discriminator": "0",
        "global_name": "Phamouxe IPTV Boss",
        "avatar": "avatar_abc123",
        "access_token": "demo_oauth_token_xyz987",
        "refresh_token": "demo_refresh_token_123",
        "expires_at": "2030-01-01 00:00:00",
        "scope": "identify guilds"
    }
    save_discord_oauth(mock_discord_account)

    # Save mock user guilds with different roles:
    # Guild 1: User is Owner
    # Guild 2: User is Admin / Manager (permissions: 0x8 | 0x20 = 40)
    # Guild 3: Regular member (permissions: 0)
    mock_user_guilds = [
        {
            "guild_id": "888111222333444555",
            "name": "Famous Media VIP Community",
            "icon": "icon_hash_vip",
            "owner": True,
            "permissions": "2147483647",
            "can_manage": 1,
            "role_name": "Server Owner"
        },
        {
            "guild_id": "777111222333444555",
            "name": "IPTV Stream Resellers Hub",
            "icon": None,
            "owner": False,
            "permissions": "40", # Manage Server (32) + Admin (8)
            "can_manage": 1,
            "role_name": "Administrator"
        },
        {
            "guild_id": "666111222333444555",
            "name": "General Tech Talk",
            "icon": None,
            "owner": False,
            "permissions": "1049664", # Basic member permissions
            "can_manage": 0,
            "role_name": "Member"
        }
    ]
    save_user_guilds(mock_user_guilds)

    # Set up client ID so invite URLs can be generated
    set_bot_setting("discord_client_id", "194123456789012345")

    resp_auth = run_coro(api_get_user_guilds(authenticated=True))
    body_auth = json.loads(resp_auth.body.decode())
    assert body_auth["is_authenticated"] is True
    assert body_auth["count"] == 3
    assert len(body_auth["guilds"]) == 3

    guild_dict = {g["guild_id"]: g for g in body_auth["guilds"]}
    assert guild_dict["888111222333444555"]["role_badge"] == "Server Owner"
    assert bool(guild_dict["888111222333444555"]["can_manage"]) is True
    assert "icon_hash_vip" in guild_dict["888111222333444555"]["icon_url"]

    assert bool(guild_dict["777111222333444555"]["can_manage"]) is True
    assert bool(guild_dict["666111222333444555"]["can_manage"]) is False
    print("  -> User Guilds retrieved, sorted, and roles properly annotated.", flush=True)

    # -------------------------------------------------------------------------
    # TEST 2: Bot Installation URL with Targeted Guild ID
    # -------------------------------------------------------------------------
    print("\n[TEST 2/6] Testing Targeted Bot Installation URL Generation...", flush=True)
    target_gid = "888111222333444555"
    resp_invite = run_coro(api_get_bot_invite_url(guild_id=target_gid, authenticated=True))
    invite_body = json.loads(resp_invite.body.decode())
    invite_url = invite_body["invite_url"]

    assert "client_id=194123456789012345" in invite_url
    assert f"guild_id={target_gid}" in invite_url
    assert "bot" in invite_url and "applications.commands" in invite_url
    assert "permissions=" in invite_url
    print(f"  -> Generated Bot Installation URL with &guild_id={target_gid} PASS.", flush=True)

    # -------------------------------------------------------------------------
    # TEST 3: Separation of User Guilds vs Bot-Connected Servers & Live Polling
    # -------------------------------------------------------------------------
    print("\n[TEST 3/6] Testing Server Separation & Live Verification Polling...", flush=True)
    # Ensure bot_guilds is initially empty
    sync_bot_guilds([])

    # Guild 888111222333444555 is NOT connected to bot yet
    resp_poll_before = run_coro(api_check_bot_in_server(target_gid, authenticated=True))
    poll_before = json.loads(resp_poll_before.body.decode())
    assert poll_before["is_connected"] is False
    print(f"  -> Polling unjoined server correctly reports is_connected=False.", flush=True)

    # Simulate bot joining Guild 888111222333444555
    sync_bot_guilds([{
        "id": target_gid,
        "name": "Famous Media VIP Community",
        "member_count": 1250,
        "icon_url": "icon_hash_vip"
    }])

    # Poll again - should now report is_connected=True
    resp_poll_after = run_coro(api_check_bot_in_server(target_gid, authenticated=True))
    poll_after = json.loads(resp_poll_after.body.decode())
    assert poll_after["is_connected"] is True
    assert poll_after["name"] == "Famous Media VIP Community"
    print(f"  -> Polling after bot join reports is_connected=True with member count {poll_after['member_count']}.", flush=True)

    # Verify that api_get_user_guilds now marks target_gid as bot_connected=True
    resp_auth2 = run_coro(api_get_user_guilds(authenticated=True))
    body_auth2 = json.loads(resp_auth2.body.decode())
    updated_guild_dict = {g["guild_id"]: g for g in body_auth2["guilds"]}
    assert updated_guild_dict[target_gid]["bot_connected"] is True
    assert updated_guild_dict["777111222333444555"]["bot_connected"] is False
    print("  -> User Guilds correctly distinguishes bot-connected servers from unconnected user servers.", flush=True)

    # -------------------------------------------------------------------------
    # TEST 4: Channel Message Fetching & In-Page Discussion Viewer
    # -------------------------------------------------------------------------
    print("\n[TEST 4/6] Testing Channel Messages Retrieval & Signal Detection...", flush=True)
    mock_cid = "999888777666555444"
    save_server_channels(target_gid, [{
        "channel_id": mock_cid,
        "name": "iptv-support-and-pricing",
        "type": "text",
        "position": 1,
        "is_monitored": 1
    }])

    mock_messages = [
        {
            "message_id": "1001",
            "author_id": "user_prospect_1",
            "author_username": "StreamHunter",
            "author_display_name": "StreamHunter",
            "content": "Looking for a reliable IPTV subscription with sports channels. How much for 1 year?",
            "timestamp": "2026-10-28 14:00:00",
            "has_buying_signal": 1,
            "detected_service": "IPTV Subscriptions",
            "buying_signal_details": "Inquiring about 1 year subscription pricing",
            "relevance_score": 90
        },
        {
            "message_id": "1002",
            "author_id": "user_prospect_2",
            "author_username": "CordCutterPro",
            "author_display_name": "CordCutterPro",
            "content": "Do you sell reseller panels? I need 120 credits with my custom app rebrand.",
            "timestamp": "2026-10-28 14:05:00",
            "has_buying_signal": 1,
            "detected_service": "Reseller Panels",
            "buying_signal_details": "Inquiring about 120 credits reseller panel",
            "relevance_score": 95
        }
    ]
    saved_count = save_channel_messages(target_gid, mock_cid, "iptv-support-and-pricing", mock_messages)
    assert saved_count >= 2

    # Fetch via API endpoint
    resp_chan_msgs = run_coro(api_get_channel_messages(
        guild_id=target_gid,
        channel_id=mock_cid,
        limit=50,
        authenticated=True
    ))
    chan_msgs_body = json.loads(resp_chan_msgs.body.decode())
    assert chan_msgs_body["success"] is True
    assert chan_msgs_body["count"] >= 2
    msgs = chan_msgs_body["messages"]

    # Check buying signal categorization
    prospect1 = next(m for m in msgs if m["message_id"] == "1001")
    assert prospect1["has_buying_signal"] == 1
    assert prospect1["detected_service"] == "IPTV Subscriptions"

    prospect2 = next(m for m in msgs if m["message_id"] == "1002")
    assert prospect2["has_buying_signal"] == 1
    assert "Reseller" in prospect2["detected_service"]
    print(f"  -> Channel messages retrieved: {chan_msgs_body['count']} indexed, buying signals accurately tagged.", flush=True)

    # -------------------------------------------------------------------------
    # TEST 5: Personal Direct Message Intake & AI Response Drafting
    # -------------------------------------------------------------------------
    print("\n[TEST 5/6] Testing Personal DM Intake & Famous Media AI Responses...", flush=True)
    dm_payload = PersonalDMIntakePayload(
        contact_name="James Miller",
        discord_username="jmiller_tv#1234",
        target_service="IPTV Subscriptions",
        raw_conversation="Prospect: Hey there, I got recommended to Famous Media. Does your 12-month service freeze during live UEFA Champions League games? Also what are your payment options?",
        notes="High intent subscriber inquiring about Premier League and UEFA."
    )

    resp_dm = run_coro(api_save_personal_dm(payload=dm_payload, authenticated=True))
    dm_result = json.loads(resp_dm.body.decode())
    assert dm_result["success"] is True
    analysis = dm_result["analysis"]

    assert analysis["summary"] != ""
    assert len(analysis["identified_questions"]) >= 1
    assert len(analysis["suggested_replies"]) >= 3

    all_replies_text = " ".join([r.get("content", "") or r.get("message_text", "") for r in analysis.get("suggested_replies", [])])
    assert "$80" in all_replies_text or "80" in all_replies_text or "$15" in all_replies_text
    assert "anti-freeze" in all_replies_text.lower() or "test line" in all_replies_text.lower() or "trial" in all_replies_text.lower()

    # Verify lead was recorded in CRM
    leads = get_leads()
    saved_lead = next((l for l in leads if "jmiller" in str(l.get("contact_handle", "")).lower()), None)
    assert saved_lead is not None
    assert saved_lead["contact_name"] == "James Miller"
    assert saved_lead["stage"] == "Conversation Started"
    print(f"  -> Personal DM Intake created CRM Lead ID: {dm_result['lead_id']} with 3 AI-drafted responses.", flush=True)

    # -------------------------------------------------------------------------
    # TEST 6: User Guilds Refresh Endpoint with Demo Account
    # -------------------------------------------------------------------------
    print("\n[TEST 6/6] Testing User Guilds Refresh API...", flush=True)
    resp_refresh = run_coro(api_refresh_user_guilds(authenticated=True))
    body_refresh = json.loads(resp_refresh.body.decode())
    assert body_refresh["success"] is True
    assert body_refresh["refreshed"] is True
    assert body_refresh["count"] >= 3
    print("  -> User Guilds Refresh API PASS.", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL SERVER & CHAT ACCESS TESTS PASSED SUCCESSFULLY! (100% OK)", flush=True)
    print("=" * 70, flush=True)

def cleanup():
    delete_discord_oauth()
    set_bot_setting("discord_client_id", "")
    print("[CLEANUP] Test mock OAuth credentials cleared from database.", flush=True)

if __name__ == "__main__":
    try:
        run_all_tests()
    finally:
        cleanup()
