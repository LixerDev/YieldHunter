import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "30"))
    MIN_TVL_USD: float = float(os.getenv("MIN_TVL_USD", "100000"))
    MIN_APY_PCT: float = float(os.getenv("MIN_APY_PCT", "0.0"))
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "20"))
    MAX_RISK_SCORE: int = int(os.getenv("MAX_RISK_SCORE", "100"))

    DEFAULT_CAPITAL_USD: float = float(os.getenv("DEFAULT_CAPITAL_USD", "10000"))
    MAX_PER_PROTOCOL_PCT: float = float(os.getenv("MAX_PER_PROTOCOL_PCT", "40"))
    MAX_PER_TOKEN_PCT: float = float(os.getenv("MAX_PER_TOKEN_PCT", "60"))
    MIN_POSITION_USD: float = float(os.getenv("MIN_POSITION_USD", "500"))

    ALERT_APY_DROP_PCT: float = float(os.getenv("ALERT_APY_DROP_PCT", "1.0"))
    ALERT_NEW_OPPORTUNITY_APY: float = float(os.getenv("ALERT_NEW_OPPORTUNITY_APY", "8.0"))
    ALERT_COOLDOWN_MINUTES: int = int(os.getenv("ALERT_COOLDOWN_MINUTES", "60"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

config = Config()
