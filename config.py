from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BILLS_WITH_RISK_PATH = DATA_DIR / "bills_with_risk.parquet"
DATABASE_PATH = DATA_DIR / "legisrisk.db"
DEFAULT_TICKERS = "AAPL, JPM, LLY"
SECRET_KEY = "legisrisk-dev-secret-key-2026"

# Database
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Security
WTF_CSRF_SECRET_KEY = "csrf-secret-key-2026"
