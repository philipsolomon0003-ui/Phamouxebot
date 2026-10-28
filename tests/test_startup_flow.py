import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_connection, init_db

def test_startup_and_auth_flow():
    init_db()

    # 0. Clean auth config for fresh setup test
    conn = get_connection()
    conn.execute("DELETE FROM auth_config WHERE key = 'admin_password_hash'")
    conn.execute("DELETE FROM user_sessions")
    conn.commit()
    conn.close()

    client = TestClient(app, follow_redirects=False)

    # 1. Opening root '/' when unconfigured should redirect to '/setup'
    res = client.get("/")
    assert res.status_code == 303, f"Expected 303 redirect, got {res.status_code}"
    assert res.headers["location"] == "/setup", f"Expected redirect to /setup, got {res.headers['location']}"
    print("[OK] Fresh unconfigured vault correctly routes to '/setup'")

    # 2. Inspect '/setup' initialization screen
    res_setup = client.get("/setup")
    assert res_setup.status_code == 200
    assert "FAMOUS MEDIA" in res_setup.text
    assert "Master Password" in res_setup.text
    print("[OK] '/setup' screen renders with sovereign credentials initialization")

    # 3. Setup master password
    master_key = "SovereignVaultKey2026!#"
    res_post_setup = client.post("/setup", data={
        "password": master_key,
        "confirm_password": master_key
    })
    assert res_post_setup.status_code == 303
    assert res_post_setup.headers["location"] == "/"
    cookies = res_post_setup.cookies
    assert "phamouxe_session" in cookies
    print("[OK] Master password setup succeeded, session cookie issued")

    # 4. Visit '/' with authenticated cookie -> opens executive dashboard
    res_dash = client.get("/", cookies=cookies)
    assert res_dash.status_code == 200
    assert "FAMOUS MEDIA" in res_dash.text or "Famous Media" in res_dash.text
    assert "Server Management" in res_dash.text
    assert "Conversation Workspace" in res_dash.text
    assert "AI Research Center" in res_dash.text
    print("[OK] Executive Dashboard renders with all modules")

    # 5. Protected API endpoints reject unauthorized access
    res_api_unauth = client.get("/api/servers")
    assert res_api_unauth.status_code == 401
    print("[OK] Protected REST endpoints return 401 Unauthorized for unauthenticated calls")

    # 6. Protected API endpoints allow access with valid session
    res_api_auth = client.get("/api/servers", cookies=cookies)
    assert res_api_auth.status_code == 200
    print("[OK] Protected REST endpoints return 200 OK with valid session cookie")

    # 7. Test Logout
    res_logout = client.get("/logout", cookies=cookies)
    assert res_logout.status_code == 303
    assert res_logout.headers["location"] == "/login"
    print("[OK] Logout terminates session and redirects to '/login'")

    # 8. Visiting '/' after logout routes to '/login'
    res_dash_logged_out = client.get("/")
    assert res_dash_logged_out.status_code == 303
    assert res_dash_logged_out.headers["location"] == "/login"
    print("[OK] Visiting dashboard after logout strictly redirects to '/login'")

    # 9. Test Invalid Password Login
    res_login_bad = client.post("/login", data={"password": "wrong-password-attempt"})
    assert res_login_bad.status_code == 200
    assert "Invalid master password" in res_login_bad.text
    print("[OK] Invalid password correctly rejected with error alert")

    # 10. Test Valid Password Login
    res_login_good = client.post("/login", data={"password": master_key})
    assert res_login_good.status_code == 303
    assert res_login_good.headers["location"] == "/"
    assert "phamouxe_session" in res_login_good.cookies
    print("[OK] Valid password authentication unlocks vault and returns to dashboard")

    # Clean up so production database remains in first-time setup state for operator
    conn = get_connection()
    conn.execute("DELETE FROM auth_config WHERE key = 'admin_password_hash'")
    conn.execute("DELETE FROM user_sessions")
    conn.commit()
    conn.close()

    print("\nALL STAGE 1 AUTHENTICATION & SECURITY TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_startup_and_auth_flow()
