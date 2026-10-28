import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.requests import Request
from starlette.responses import RedirectResponse
from app.database import init_db, get_connection
from app.auth import is_admin_configured, set_admin_password, check_admin_password, create_session, validate_session, destroy_session
from app.main import setup_get, setup_post, login_get, login_post, logout, index_view

def run_coro(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")

def run_auth_tests():
    init_db()
    # 1. Reset auth state
    conn = get_connection()
    conn.execute("DELETE FROM auth_config WHERE key = 'admin_password_hash'")
    conn.execute("DELETE FROM user_sessions")
    conn.commit()
    conn.close()

    assert is_admin_configured() is False
    print("[OK] Initial vault state: unconfigured.")

    # 2. Test setup_get when unconfigured -> renders setup.html
    req = Request({"type": "http", "method": "GET", "headers": [], "path": "/setup"})
    resp = run_coro(setup_get(req))
    assert resp.status_code == 200
    print("[OK] /setup endpoint returns 200 setup screen when vault is uninitialized.")

    # 3. Test setup_post password mismatch -> renders error
    resp_mismatch = run_coro(setup_post(req, password="Password123#", confirm_password="MismatchPassword!"))
    assert resp_mismatch.status_code == 200
    assert "Passwords do not match" in resp_mismatch.body.decode()
    print("[OK] Password mismatch validation verified.")

    # 4. Test setup_post with valid password -> sets master key and redirects to '/' with cookie
    master_key = "PhamouxeMasterKey2026!#"
    resp_setup_ok = run_coro(setup_post(req, password=master_key, confirm_password=master_key))
    assert resp_setup_ok.status_code == 303
    assert resp_setup_ok.headers["location"] == "/"
    cookie_header = resp_setup_ok.headers.get("set-cookie")
    assert "phamouxe_session=" in cookie_header
    assert is_admin_configured() is True
    print("[OK] Master password successfully initialized with PBKDF2 hash.")

    # 5. Extract session token
    token = cookie_header.split("phamouxe_session=")[1].split(";")[0]
    assert validate_session(token) is True
    print("[OK] Session token verified in database.")

    # 6. Test index_view with valid session -> renders dashboard
    cookie_bytes = f"phamouxe_session={token}".encode()
    req_auth = Request({
        "type": "http",
        "method": "GET",
        "headers": [(b"cookie", cookie_bytes)],
        "path": "/"
    })
    resp_dash = run_coro(index_view(req_auth))
    assert resp_dash.status_code == 200
    body = resp_dash.body.decode()
    assert "FAMOUS MEDIA" in body or "Famous Media Technologies" in body
    assert "Server Management" in body
    assert "Conversation Workspace" in body
    assert "AI Research Center" in body
    print("[OK] Private Executive Dashboard renders for authenticated operator.")

    # 7. Test index_view without session -> redirects to /login
    req_unauth = Request({
        "type": "http",
        "method": "GET",
        "headers": [],
        "path": "/"
    })
    resp_unauth = run_coro(index_view(req_unauth))
    assert resp_unauth.status_code == 303
    assert resp_unauth.headers["location"] == "/login"
    print("[OK] Unauthenticated visit to dashboard strictly redirects to /login.")

    # 8. Test login_post with wrong password -> renders error
    resp_bad_login = run_coro(login_post(req_unauth, password="WrongPassword!"))
    assert resp_bad_login.status_code == 200
    assert "Invalid master password" in resp_bad_login.body.decode()
    print("[OK] Invalid password attempt correctly rejected.")

    # 9. Test login_post with correct password -> redirects to / with new session cookie
    resp_good_login = run_coro(login_post(req_unauth, password=master_key))
    assert resp_good_login.status_code == 303
    assert resp_good_login.headers["location"] == "/"
    assert "phamouxe_session=" in resp_good_login.headers.get("set-cookie")
    print("[OK] Correct master password authenticates and issues new session cookie.")

    # 10. Test logout -> terminates session and redirects to /login
    resp_logout = run_coro(logout(req_auth))
    assert resp_logout.status_code == 303
    assert resp_logout.headers["location"] == "/login"
    assert validate_session(token) is False
    print("[OK] Logout terminates active session in vault and routes to /login.")

    # 11. Test /reset-password endpoint
    from app.main import reset_password_get, reset_password_post, api_change_password, ChangePasswordPayload
    from app.config import ADMIN_SECRET_KEY
    resp_reset_get = run_coro(reset_password_get(req_unauth))
    assert resp_reset_get.status_code == 200
    assert "Reset Master Password" in resp_reset_get.body.decode()
    print("[OK] /reset-password screen renders for operator.")

    # 12. Test /reset-password with invalid secret key -> rejects
    resp_reset_bad = run_coro(reset_password_post(
        req_unauth,
        secret_key="WrongSecretKey!",
        new_password="NewSecretPass2026!",
        confirm_new_password="NewSecretPass2026!"
    ))
    assert resp_reset_bad.status_code == 200
    assert "Invalid Application Secret Key" in resp_reset_bad.body.decode()
    print("[OK] Password reset rejects unauthorized secret key.")

    # 13. Test /reset-password with valid secret key -> resets password and issues session
    new_master_pass = "FamousMediaSecretPass2026!"
    resp_reset_ok = run_coro(reset_password_post(
        req_unauth,
        secret_key=ADMIN_SECRET_KEY,
        new_password=new_master_pass,
        confirm_new_password=new_master_pass
    ))
    assert resp_reset_ok.status_code == 303
    assert resp_reset_ok.headers["location"] == "/"
    assert check_admin_password(new_master_pass) is True
    print("[OK] Password reset with valid secret key updates password and logs in.")

    # 14. Test in-dashboard password change
    payload_change = ChangePasswordPayload(
        current_password=new_master_pass,
        new_password="ChangedFamousPassword2026!",
        confirm_new_password="ChangedFamousPassword2026!"
    )
    resp_change = run_coro(api_change_password(payload_change, authenticated=True))
    assert resp_change.status_code == 200
    assert check_admin_password("ChangedFamousPassword2026!") is True
    print("[OK] In-dashboard password change verified.")

    # 15. Final Clean Slate: reset master password so operator experiences first-time setup
    from app.reset_password import reset_master_password
    reset_master_password()
    assert is_admin_configured() is False
    print("[OK] Production database returned to clean First-Time Setup state for operator.")

    print("\nALL STAGE 1 AUTHENTICATION & VAULT TESTS COMPLETED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_auth_tests()
