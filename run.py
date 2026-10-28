import os
import sys
import threading
import time
import webbrowser
import uvicorn
from app.config import HOST, PORT, DEBUG

def open_browser_delayed():
    time.sleep(1.8)
    url = f"http://{HOST}:{PORT}"
    print(f"\n[PHAMOUXE] Opening your browser to: {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 70)
    print("   FAMOUS MEDIA TECHNOLOGIES | DISCORD AI BUSINESS ASSISTANT")
    print("   Personal IPTV Research, Networking, CRM & Follow-Up Suite")
    print("=" * 70)
    print(f"   [Status] Initializing secure local server on http://{HOST}:{PORT}")
    print(f"   [Theme]  Obsidian Charcoal, Deep Navy & Restrained Blue Accents")
    print("   [Contact] Direct Telegram: @Phamouxetv")
    print("=" * 70)

    # Automatically open the web browser for the operator
    threading.Thread(target=open_browser_delayed, daemon=True).start()

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, log_level="info", proxy_headers=True, forwarded_allow_ips="*")
