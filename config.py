from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BILLS_WITH_RISK_PATH = DATA_DIR / "bills_with_risk.parquet"
DATABASE_PATH = DATA_DIR / "legisrisk.db"
DEFAULT_TICKERS = "AAPL, JPM, LLY"
