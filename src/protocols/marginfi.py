"""
MarginFi fetcher.

MarginFi is a lending protocol on Solana with:
- Isolated lending markets (bank groups)
- Supply + borrow for SOL, USDC, USDT, and many SPL tokens

Public API: https://production.marginfi.com/
"""

from src.models import YieldOpportunity, Protocol, YieldType
from src.protocols.base import BaseProtocolFetcher, compute_risk_score, risk_level_from_score

# MarginFi public endpoint — returns bank data with APY
BANKS_URL     = "https://production.marginfi.com/banks"
ANALYTICS_URL = "https://production.marginfi.com/bank_analytics"

# MarginFi main group
MAIN_GROUP = "4qp6Fx6tnZkY5Wropq9wUYgtFxXKwE6viZxFHg3rdAG4"


class MarginFiFetcher(BaseProtocolFetcher):
    protocol = Protocol.MARGINFI

    async def fetch(self) -> list[YieldOpportunity]:
        opportunities = []

        # Try primary analytics endpoint
        data = await self._get(ANALYTICS_URL)
        if data:
            banks = data if isinstance(data, list) else data.get("banks", data.get("data", []))
            for bank in banks:
                opp = self._parse_bank(bank)
                if opp:
                    opportunities.append(opp)

        # Fallback: try /banks endpoint
        if not opportunities:
            data = await self._get(BANKS_URL)
            if data:
                banks = data if isinstance(data, list) else data.get("banks", [])
                for bank in banks:
                    opp = self._parse_bank(bank)
                    if opp:
                        opportunities.append(opp)

        self.logger.info(f"MarginFi: {len(opportunities)} opportunities fetched")
        return opportunities

    def _parse_bank(self, bank: dict) -> YieldOpportunity | None:
        """Parse a MarginFi bank into a YieldOpportunity."""
        symbol = (
            bank.get("tokenSymbol") or
            bank.get("symbol") or
            bank.get("mint_symbol", "???")
        )
        if symbol in ("???", "") or not symbol:
            return None

        mint = bank.get("mint") or bank.get("address", "")

        # APY extraction — MarginFi returns as percentages or decimals
        raw_supply = bank.get("deposit_rate") or bank.get("depositApy") or bank.get("supplyApy", 0)
        raw_borrow = bank.get("borrow_rate") or bank.get("borrowApy", 0)
        raw_reward = bank.get("emissionsRate") or bank.get("rewardApy", 0)

        # Normalize: if value > 1, treat as pct already; if < 1, multiply by 100
        def normalize(v) -> float:
            v = float(v or 0)
            return v if v > 1 else v * 100

        supply_apy = normalize(raw_supply)
        borrow_apy = normalize(raw_borrow)
        reward_apy = normalize(raw_reward)
        total_apy  = supply_apy + reward_apy

        tvl_usd = float(
            bank.get("totalAssets") or
            bank.get("tvl") or
            bank.get("depositedValue", 0)
        )

        utilization = float(
            bank.get("utilizationRate") or
            bank.get("utilization", 0.5)
        )
        # Normalize utilization to 0-100
        if utilization <= 1:
            utilization *= 100

        available = float(bank.get("availableLiquidity") or tvl_usd * (1 - utilization / 100))

        risk = compute_risk_score(Protocol.MARGINFI, tvl_usd, utilization)

        bank_addr = bank.get("bankAddress") or bank.get("address") or mint[:16]

        return YieldOpportunity(
            opportunity_id=f"marginfi_{bank_addr[:8]}",
            protocol=Protocol.MARGINFI,
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
            pool_address=bank_addr,
            reward_token="MRGN",
            url=f"https://app.marginfi.com/",
        )
