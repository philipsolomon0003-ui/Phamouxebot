"""
Famous Media Technologies — Master Password Reset Utility
Clears master password hash and active sessions so operator can set a fresh password.
All customer leads, discovered servers, messages, notes, and business settings are 100% PRESERVED.
"""
import sys
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database import get_connection

def reset_master_password():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auth_config WHERE key = 'admin_password_hash'")
    cursor.execute("DELETE FROM user_sessions")
    conn.commit()
    conn.close()
    print("=" * 68)
    print("   FAMOUS MEDIA TECHNOLOGIES | MASTER PASSWORD RESET")
    print("=" * 68)
    print("   [SUCCESS] Master password has been cleared successfully!")
    print("   [SAFE]    All customer leads, research, and settings are 100% preserved.")
    print("   [ACTION]  Opening http://127.0.0.1:8080/setup to create your new password...")
    print("=" * 68)
    try:
        webbrowser.open("http://127.0.0.1:8080/setup")
    except Exception:
        pass

if __name__ == "__main__":
    reset_master_password()
