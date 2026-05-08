import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BILLS_WITH_RISK_PATH = DATA_DIR / "bills_with_risk.parquet"
DEFAULT_DB_FILENAME = "legisrisk.db"
DEFAULT_DATABASE_PATH = DATA_DIR / DEFAULT_DB_FILENAME
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH))
DEFAULT_TICKERS = "AAPL, JPM, LLY"
SECRET_KEY = "legisrisk-dev-secret-key-2026"

# Database
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URI:
    db_dir = DATABASE_PATH.parent
    if not db_dir.exists() or not os.access(db_dir, os.W_OK):
        DATABASE_PATH = Path(tempfile.gettempdir()) / DEFAULT_DB_FILENAME
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

SQLALCHEMY_TRACK_MODIFICATIONS = False

# Security
WTF_CSRF_SECRET_KEY = "csrf-secret-key-2026"
