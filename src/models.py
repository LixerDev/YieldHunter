from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class Protocol(str, Enum):
    KAMINO   = "Kamino"
    MARGINFI = "MarginFi"
    SOLEND   = "Solend"
    DRIFT    = "Drift"
    MANGO    = "Mango"
    UNKNOWN  = "Unknown"


class YieldType(str, Enum):
    SUPPLY = "Supply"       # Earn by depositing
    BORROW = "Borrow"       # Cost to borrow
    LP     = "LP"           # Liquidity provision
    VAULT  = "Vault"        # Managed strategy vault


class RiskLevel(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


PROTOCOL_COLORS = {
    Protocol.KAMINO:   "bright_blue",
    Protocol.MARGINFI: "bright_cyan",
    Protocol.SOLEND:   "bright_green",
    Protocol.DRIFT:    "bright_yellow",
    Protocol.MANGO:    "bright_magenta",
    Protocol.UNKNOWN:  "dim",
}

# Protocol base risk (lower = safer, based on age + audit + TVL history)
PROTOCOL_BASE_RISK = {
    Protocol.SOLEND:   10,   # Oldest, most audited
    Protocol.KAMINO:   15,
    Protocol.MARGINFI: 20,
    Protocol.DRIFT:    25,
    Protocol.MANGO:    30,
    Protocol.UNKNOWN:  50,
}


@dataclass
class YieldOpportunity:
    """A single yield-generating opportunity on a DeFi protocol."""
    opportunity_id: str
    protocol: Protocol
    token_symbol: str
    token_mint: str
    yield_type: YieldType

    # APY components
    supply_apy: float          # Base lending/supply APY (%)
    reward_apy: float          # Bonus token rewards APY (%)
    total_apy: float           # supply_apy + reward_apy
    borrow_apy: float          # Cost to borrow (%)

    # Market data
    tvl_usd: float             # Total Value Locked in USD
    utilization_pct: float     # Current utilization rate (0–100)
    available_liquidity_usd: float  # Available to deposit/withdraw

    # Risk
    risk_score: float          # 0–100, lower = safer
    risk_level: RiskLevel

    # Meta
    pool_address: str = ""
    reward_token: str = ""     # Token given as reward
    url: str = ""
    fetched_at: float = field(default_factory=time.time)

    @property
    def risk_adjusted_apy(self) -> float:
        """APY adjusted for risk: penalizes high-risk positions."""
        penalty = self.risk_score / 200  # 0 to 0.5 penalty
        return self.total_apy * (1 - penalty)

    @property
    def is_high_yield(self) -> bool:
        return self.total_apy >= 8.0

    def weekly_yield(self, capital_usd: float) -> float:
        return capital_usd * (self.total_apy / 100) / 52

    def annual_yield(self, capital_usd: float) -> float:
        return capital_usd * (self.total_apy / 100)

    def to_dict(self) -> dict:
        return {
            "protocol": self.protocol.value,
            "token": self.token_symbol,
            "type": self.yield_type.value,
            "supply_apy": round(self.supply_apy, 2),
            "reward_apy": round(self.reward_apy, 2),
            "total_apy": round(self.total_apy, 2),
            "borrow_apy": round(self.borrow_apy, 2),
            "tvl_usd": round(self.tvl_usd),
            "utilization_pct": round(self.utilization_pct, 1),
            "risk_score": round(self.risk_score),
            "risk_level": self.risk_level.value,
        }


@dataclass
class AllocationSlice:
    """One slice of a capital allocation plan."""
    opportunity: YieldOpportunity
    amount_usd: float
    pct_of_total: float

    @property
    def weekly_yield(self) -> float:
        return self.opportunity.weekly_yield(self.amount_usd)

    @property
    def annual_yield(self) -> float:
        return self.opportunity.annual_yield(self.amount_usd)


@dataclass
class AllocationPlan:
    """Complete capital allocation plan across multiple opportunities."""
    total_capital: float
    slices: list[AllocationSlice] = field(default_factory=list)

    @property
    def blended_apy(self) -> float:
        if not self.slices:
            return 0.0
        return sum(s.opportunity.total_apy * (s.amount_usd / self.total_capital)
                   for s in self.slices)

    @property
    def total_weekly_yield(self) -> float:
        return sum(s.weekly_yield for s in self.slices)

    @property
    def total_annual_yield(self) -> float:
        return sum(s.annual_yield for s in self.slices)
