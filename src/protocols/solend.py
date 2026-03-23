"""
Solend fetcher.

Solend is the oldest lending protocol on Solana.
Offers multiple isolated lending pools with supply/borrow APY.

Public API: https://api.solend.fi/v1/
"""

from src.models import YieldOpportunity, Protocol, YieldType
from src.protocols.base import BaseProtocolFetcher, compute_risk_score, risk_level_from_score

CONFIG_URL  = "https://api.solend.fi/v1/markets/configs?deployment=production"
RATES_URL   = "https://api.solend.fi/v1/markets/"


class SolendFetcher(BaseProtocolFetcher):
    protocol = Protocol.SOLEND

    async def fetch(self) -> list[YieldOpportunity]:
        config_data = await self._get(CONFIG_URL)
        if not config_data:
            self.logger.warning("Solend config not available")
            return []

        markets = config_data if isinstance(config_data, list) else config_data.get("markets", [])
        opportunities = []

        for market in markets:
            market_name = market.get("name", "")
            market_addr = market.get("address") or market.get("pubkey", "")
            reserves = market.get("reserves", [])

            for reserve in reserves:
                opp = self._parse_reserve(reserve, market_name, market_addr)
                if opp:
                    opportunities.append(opp)

        self.logger.info(f"Solend: {len(opportunities)} opportunities fetched")
        return opportunities

    def _parse_reserve(self, reserve: dict, market_name: str, market_addr: str) -> YieldOpportunity | None:
        """Parse a Solend reserve into a YieldOpportunity."""
        asset = reserve.get("asset") or reserve.get("symbol", "???")
        if asset in ("???", ""):
            return None

        mint_address = reserve.get("mintAddress") or reserve.get("mint", "")

        # Rate data (may be nested)
        rates = reserve.get("rates") or reserve
        supply_apy = float(rates.get("supplyInterest") or rates.get("supplyApy", 0))
        borrow_apy = float(rates.get("borrowInterest") or rates.get("borrowApy", 0))

        # Normalize: Solend typically returns already in % (e.g. 5.82)
        # But sometimes in decimal (0.0582)
        if supply_apy < 1 and supply_apy > 0:
            supply_apy *= 100
            borrow_apy *= 100

        # Mining rewards
        mining = reserve.get("miningBorrowApy") or reserve.get("miningSupplyApy", 0)
        reward_apy = float(mining or 0)
        if reward_apy < 1 and reward_apy > 0:
            reward_apy *= 100

        total_apy = supply_apy + reward_apy

        # TVL
        tvl_usd = float(
            reserve.get("totalSupplyUSD") or
            reserve.get("depositedValue") or
            reserve.get("tvl", 0)
        )

        # Utilization
        raw_util = reserve.get("utilizationRate") or reserve.get("utilization", 0.6)
        utilization = float(raw_util)
        if utilization <= 1:
            utilization *= 100

        available = float(reserve.get("availableLiquidityUSD") or tvl_usd * (1 - utilization / 100))

        reserve_addr = reserve.get("reserveAddress") or reserve.get("address", mint_address[:16])
        risk = compute_risk_score(Protocol.SOLEND, tvl_usd, utilization)

        return YieldOpportunity(
            opportunity_id=f"solend_{reserve_addr[:8]}",
            protocol=Protocol.SOLEND,
            token_symbol=asset,
            token_mint=mint_address,
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
            pool_address=market_addr,
            reward_token="SLND",
            url=f"https://solend.fi/dashboard",
        )
