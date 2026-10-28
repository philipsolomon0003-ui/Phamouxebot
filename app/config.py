import os
from pathlib import Path
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "phamouxe.db"

# Admin / Auth settings
ADMIN_SECRET_KEY = os.getenv("PHAMOUXE_SECRET_KEY", "phamouxe-luxury-sovereign-vault-key-2026")
COOKIE_NAME = "phamouxe_session"
SESSION_DURATION_HOURS = 24

# App Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 8080))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
