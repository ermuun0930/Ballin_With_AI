import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BILLS_WITH_RISK_PATH = Path(os.environ.get("BILLS_WITH_RISK_PATH", DATA_DIR / "bills_with_risk.parquet"))
DEFAULT_DB_FILENAME = "legisrisk.db"
DEFAULT_ANALYTICS_DATABASE_PATH = DATA_DIR / DEFAULT_DB_FILENAME
ANALYTICS_DATABASE_PATH = Path(os.environ.get("ANALYTICS_DATABASE_PATH", DEFAULT_ANALYTICS_DATABASE_PATH))
DEFAULT_TICKERS = "AAPL, JPM, LLY"
SECRET_KEY = "legisrisk-dev-secret-key-2026"

# LegisRisk AWS API
RISK_API_URL = os.environ.get(
    "RISK_API_URL",
    "https://o13e3w95bk.execute-api.us-east-1.amazonaws.com/Prod/risk",
)
RISK_API_TIMEOUT = int(os.environ.get("RISK_API_TIMEOUT", "90"))
RISK_API_ANALYZE_IMPACT = os.environ.get("RISK_API_ANALYZE_IMPACT", "true").lower() == "true"

# Application database
APP_DATABASE_PATH = Path(os.environ.get("APP_DATABASE_PATH", ANALYTICS_DATABASE_PATH))
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URI:
    app_db_dir = APP_DATABASE_PATH.parent
    if not app_db_dir.exists() or not os.access(app_db_dir, os.W_OK):
        APP_DATABASE_PATH = Path(tempfile.gettempdir()) / DEFAULT_DB_FILENAME
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{APP_DATABASE_PATH}"

# Keep the old config key for backward compatibility to analytics DB path
DATABASE_PATH = ANALYTICS_DATABASE_PATH
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Security
WTF_CSRF_SECRET_KEY = "csrf-secret-key-2026"
