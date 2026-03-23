"""
Base class for all protocol fetchers.
"""

import aiohttp
from abc import ABC, abstractmethod
from src.models import YieldOpportunity, Protocol, RiskLevel, PROTOCOL_BASE_RISK
from src.logger import get_logger

TIMEOUT = aiohttp.ClientTimeout(total=12)


def compute_risk_score(
    protocol: Protocol,
    tvl_usd: float,
    utilization_pct: float,
) -> float:
    """
    Compute a risk score (0–100) for a yield opportunity.

    Factors:
    - Protocol base risk (age + audit history)
    - TVL: Higher TVL = lower risk
    - Utilization: 40–80% is healthy; extremes are riskier

    Returns:
    - float: Risk score where 0 = safest, 100 = highest risk
    """
    base = PROTOCOL_BASE_RISK.get(protocol, 50)

    # TVL risk factor: $500M+ = 0 penalty, <$1M = 30 penalty
    if tvl_usd >= 500_000_000:
        tvl_risk = 0
    elif tvl_usd >= 100_000_000:
        tvl_risk = 10
    elif tvl_usd >= 10_000_000:
        tvl_risk = 20
    elif tvl_usd >= 1_000_000:
        tvl_risk = 30
    else:
        tvl_risk = 40

    # Utilization risk: 40–80% is optimal
    util = utilization_pct
    if 40 <= util <= 80:
        util_risk = 0
    elif util > 90:
        util_risk = 25    # Very high utilization = liquidity risk
    elif util > 80:
        util_risk = 10
    elif util < 10:
        util_risk = 5     # Very low utilization = low demand signal
    else:
        util_risk = 5

    score = base + tvl_risk * 0.4 + util_risk * 0.3
    return min(100, max(0, score))


def risk_level_from_score(score: float) -> RiskLevel:
    if score <= 30:
        return RiskLevel.LOW
    elif score <= 60:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


class BaseProtocolFetcher(ABC):
    """Abstract base for all protocol fetchers."""

    protocol: Protocol = Protocol.UNKNOWN
    logger = None

    def __init__(self):
        self.logger = get_logger(f"protocols.{self.protocol.value.lower()}")

    @abstractmethod
    async def fetch(self) -> list[YieldOpportunity]:
        """Fetch all yield opportunities from this protocol."""
        ...

    async def _get(self, url: str, params: dict = None, headers: dict = None) -> dict | list | None:
        """HTTP GET helper with error handling."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    headers=headers or {},
                    timeout=TIMEOUT
                ) as resp:
                    if resp.status == 200:
                        return await resp.json(content_type=None)
                    self.logger.warning(f"HTTP {resp.status} from {url}")
                    return None
        except Exception as e:
            self.logger.error(f"Request failed [{url}]: {e}")
            return None
