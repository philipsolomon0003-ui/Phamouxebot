import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import threading
import time
import json
import urllib.request
import urllib.error
import uvicorn
from app.main import app
from app.auth import create_session
from app.config import COOKIE_NAME
from app.database import delete_discord_oauth, init_db

def run():
    config = uvicorn.Config(app, host="127.0.0.1", port=8099, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

t = threading.Thread(target=run, daemon=True)
t.start()
time.sleep(2)

try:
    init_db()
    delete_discord_oauth()

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            return fp
        http_error_303 = http_error_302
        http_error_307 = http_error_302

    no_redirect_opener = urllib.request.build_opener(NoRedirectHandler)

    # 1. Root '/' redirects to '/connect' when not connected
    req = urllib.request.Request("http://127.0.0.1:8099/")
    resp = no_redirect_opener.open(req)
    loc = resp.headers.get("Location")
    assert "/connect" in loc
    print("[OK] Initial visit to '/' routes to '/connect' startup screen")

    # 2. Inspect '/connect' screen
    req = urllib.request.Request("http://127.0.0.1:8099/connect")
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8')
        assert resp.status == 200
        assert "Discord Account Authorization" in content
        assert "Official Discord Policy: QR-Code & Self-Bot Notice" in content
        print("[OK] '/connect' screen renders with official OAuth2 and QR policy notice")

    # 3. Test demo connect
    demo_req = urllib.request.Request("http://127.0.0.1:8099/api/auth/discord/demo-connect", data=b"", method="POST")
    demo_resp = no_redirect_opener.open(demo_req)
    set_cookie = demo_resp.headers.get("Set-Cookie")
    assert set_cookie is not None
    session_cookie = set_cookie.split(";")[0]
    print("[OK] Demo connect authorized successfully")

    # 4. Visit '/' with cookie -> loads 9-section dashboard
    dash_req = urllib.request.Request("http://127.0.0.1:8099/")
    dash_req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(dash_req) as resp:
        content = resp.read().decode('utf-8')
        assert resp.status == 200
        assert "PHAMOUXE" in content
        assert "Overview" in content
        assert "Server Discovery" in content
        assert "Saved Communities" in content
        assert "Customer Research" in content
        assert "Message Assistant" in content
        assert "Follow-up Reminders" in content
        assert "Campaign Planner" in content
        assert "Activity History" in content
        assert "Settings & Gateway" in content
        print("[OK] Dashboard renders all 9 executive navigation sections")

    # 5. Check Overview Stats API
    req = urllib.request.Request("http://127.0.0.1:8099/api/stats")
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        assert data["total_servers"] >= 8
        assert data["saved_leads"] >= 1
        print(f"[OK] /api/stats verified: {data['total_servers']} servers, {data['saved_leads']} leads")

    # 6. Check Saved Communities API
    req = urllib.request.Request("http://127.0.0.1:8099/api/saved-communities")
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        saved = json.loads(resp.read().decode('utf-8'))
        assert len(saved) >= 1
        print(f"[OK] /api/saved-communities returned {len(saved)} bookmarked hubs")

    # 7. Check Follow-Ups API
    req = urllib.request.Request("http://127.0.0.1:8099/api/follow-ups")
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        fu = json.loads(resp.read().decode('utf-8'))
        assert "overdue" in fu and "upcoming" in fu
        print(f"[OK] /api/follow-ups returned {len(fu['overdue'])} overdue and {len(fu['upcoming'])} upcoming")

    # 8. Check Generic Draft API for an IPTV service
    draft_payload = json.dumps({
        "category": "App Rebranding",
        "business_name": "Nova Rebrand",
        "contact_name": "Elena",
        "tone": "Direct"
    }).encode('utf-8')
    req = urllib.request.Request("http://127.0.0.1:8099/api/messages/draft-generic", data=draft_payload, headers={"Content-Type": "application/json"})
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        draft = json.loads(resp.read().decode('utf-8'))
        assert "Elena" in draft["content"]
        assert "XCIPTV" in draft["content"]
        print("[OK] /api/messages/draft-generic generated white-label rebranding pitch")

    # 9. Check Conversation Analysis API
    convo_payload = json.dumps({
        "conversation_text": "Client: Can you build custom Smarters for our panel? Do you offer test lines?",
        "service_type": "App Rebranding",
        "contact_name": "Client"
    }).encode('utf-8')
    req = urllib.request.Request("http://127.0.0.1:8099/api/conversation/analyze", data=convo_payload, headers={"Content-Type": "application/json"})
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        analysis = json.loads(resp.read().decode('utf-8'))
        assert len(analysis["suggested_replies"]) == 3
        print(f"[OK] /api/conversation/analyze generated 3 contextual replies")

    # 10. Check Campaigns API
    req = urllib.request.Request("http://127.0.0.1:8099/api/campaigns")
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        camps = json.loads(resp.read().decode('utf-8'))
        assert len(camps) >= 1
        print(f"[OK] /api/campaigns returned {len(camps)} campaigns")

    # 11. Check Activity API
    req = urllib.request.Request("http://127.0.0.1:8099/api/activity")
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        acts = json.loads(resp.read().decode('utf-8'))
        assert len(acts) >= 1
        print(f"[OK] /api/activity returned {len(acts)} log events")

    # 12. Check PostgreSQL Export API
    req = urllib.request.Request("http://127.0.0.1:8099/api/export/sql")
    req.add_header("Cookie", session_cookie)
    with urllib.request.urlopen(req) as resp:
        sql = resp.read().decode('utf-8')
        assert "discovered_servers" in sql
        print(f"[OK] /api/export/sql delivered {len(sql)} bytes of SQL dump")

    # 13. Test Disconnect
    disc_req = urllib.request.Request(
        "http://127.0.0.1:8099/api/auth/discord/disconnect",
        data=b"",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/html"},
        method="POST"
    )
    disc_req.add_header("Cookie", session_cookie)
    disc_resp = no_redirect_opener.open(disc_req)
    assert "/connect" in disc_resp.headers.get("Location")
    print("[OK] Disconnect resets integration and routes back to '/connect'")

    print("\nALL 13 LIVE SERVER & 9-SECTION MODULE TESTS PASSED!")

except Exception as e:
    print(f"Error during live test: {e}")
    sys.exit(1)
