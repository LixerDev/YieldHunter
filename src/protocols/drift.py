"""
Drift Protocol fetcher.

Drift offers spot market borrowing/lending alongside its perps exchange.
Depositing collateral into Drift earns interest from borrowers.

Public stats API: https://mainnet-beta.drift.trade/
"""

from src.models import YieldOpportunity, Protocol, YieldType
from src.protocols.base import BaseProtocolFetcher, compute_risk_score, risk_level_from_score

STATS_URL      = "https://mainnet-beta.drift.trade/stats"
SPOT_STATS_URL = "https://mainnet-beta.drift.trade/spotMarkets"

# Known Drift spot market indices
DRIFT_SPOT_MARKETS = {
    0:  ("USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    1:  ("SOL",  "So11111111111111111111111111111111111111112"),
    2:  ("BTC",  "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"),
    3:  ("ETH",  "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"),
    4:  ("USDT", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
    5:  ("mSOL", "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So"),
    17: ("JTO",  "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL"),
    18: ("JUP",  "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"),
}


class DriftFetcher(BaseProtocolFetcher):
    protocol = Protocol.DRIFT

    async def fetch(self) -> list[YieldOpportunity]:
        opportunities = []

        # Try spot markets endpoint
        data = await self._get(SPOT_STATS_URL)
        if data:
            markets = data if isinstance(data, list) else data.get("spotMarkets", data.get("markets", []))
            for market in markets:
                opp = self._parse_spot_market(market)
                if opp:
                    opportunities.append(opp)

        # Fallback to stats endpoint
        if not opportunities:
            data = await self._get(STATS_URL)
            if data:
                markets = data.get("spotMarkets") or data.get("markets", [])
                for market in markets:
                    opp = self._parse_spot_market(market)
                    if opp:
                        opportunities.append(opp)

        self.logger.info(f"Drift: {len(opportunities)} opportunities fetched")
        return opportunities

    def _parse_spot_market(self, market: dict) -> YieldOpportunity | None:
        """Parse a Drift spot market into a YieldOpportunity."""
        market_idx = market.get("marketIndex", market.get("index", -1))
        symbol = market.get("symbol") or market.get("name", "")

        # Fallback to known markets by index
        if not symbol and market_idx in DRIFT_SPOT_MARKETS:
            symbol, _ = DRIFT_SPOT_MARKETS[market_idx]

        if not symbol:
            return None

        mint = market.get("mint") or ""
        if not mint and market_idx in DRIFT_SPOT_MARKETS:
            _, mint = DRIFT_SPOT_MARKETS[market_idx]

        # APY extraction
        deposit_rate = market.get("depositRate") or market.get("supplyRate") or market.get("depositApy", 0)
        borrow_rate  = market.get("borrowRate") or market.get("borrowApy", 0)
        reward_rate  = market.get("emissionsApy") or market.get("rewardApy", 0)

        def normalize(v) -> float:
            v = float(v or 0)
            return v if v > 1 else v * 100

        supply_apy = normalize(deposit_rate)
        borrow_apy = normalize(borrow_rate)
        reward_apy = normalize(reward_rate)
        total_apy  = supply_apy + reward_apy

        # TVL
        tvl_usd = float(
            market.get("totalDepositsUSD") or
            market.get("totalDeposits") or
            market.get("tvl", 0)
        )

        # Utilization
        raw_util = market.get("utilizationRate") or market.get("utilization", 0.5)
        utilization = float(raw_util)
        if utilization <= 1:
            utilization *= 100

        available = tvl_usd * (1 - utilization / 100)
        risk = compute_risk_score(Protocol.DRIFT, tvl_usd, utilization)

        return YieldOpportunity(
            opportunity_id=f"drift_{market_idx}_{symbol}",
            protocol=Protocol.DRIFT,
            token_symbol=symbol,
            token_mint=mint,
            yield_type=YieldType.SUPPLY,
            supply_apy=supply_apy,
            reward_apy=reward_apy,
            total_apy=total_apy,
            borrow_apy=borrow_apy,
            tvl_usd=tvl_usd,
            utilization_pct=utilization,
            available_liquidity_usd=available,
            risk_score=risk,
            risk_level=risk_level_from_score(risk),
            pool_address=f"drift_spot_{market_idx}",
            reward_token="DRIFT",
            url=f"https://app.drift.trade/earn",
        )
