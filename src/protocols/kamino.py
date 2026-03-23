"""
Kamino Finance fetcher.

Kamino offers two main products with yield:
1. Lending markets (lend/borrow any token)
2. Liquidity strategies (automated LP vaults)

Public API: https://api.kamino.finance/
"""

import uuid
from src.models import YieldOpportunity, Protocol, YieldType
from src.protocols.base import BaseProtocolFetcher, compute_risk_score, risk_level_from_score

STRATEGIES_URL = "https://api.kamino.finance/strategies"
LENDING_URL    = "https://api.kamino.finance/v2/lending-markets"

# Kamino lending market addresses (main ones)
KAMINO_MARKETS = [
    "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF",   # Main market
    "DxXdAyU3kCjnyggvHmY5nAwg5cRbbmdyX3npfDMjjMek",   # JLP market
]


class KaminoFetcher(BaseProtocolFetcher):
    protocol = Protocol.KAMINO

    async def fetch(self) -> list[YieldOpportunity]:
        opportunities = []

        # Fetch lending market data
        lending = await self._fetch_lending()
        opportunities.extend(lending)

        # Fetch strategy vaults
        vaults = await self._fetch_strategies()
        opportunities.extend(vaults)

        self.logger.info(f"Kamino: {len(opportunities)} opportunities fetched")
        return opportunities

    async def _fetch_lending(self) -> list[YieldOpportunity]:
        """Fetch Kamino lending markets (supply/borrow APY)."""
        opportunities = []

        for market_addr in KAMINO_MARKETS:
            data = await self._get(f"{LENDING_URL}/{market_addr}/reserves")
            if not data:
                continue

            reserves = data if isinstance(data, list) else data.get("reserves", [])

            for reserve in reserves:
                try:
                    opp = self._parse_reserve(reserve, market_addr)
                    if opp:
                        opportunities.append(opp)
                except Exception as e:
                    self.logger.debug(f"Reserve parse error: {e}")

        return opportunities

    def _parse_reserve(self, reserve: dict, market_addr: str) -> YieldOpportunity | None:
        """Parse a Kamino reserve into a YieldOpportunity."""
        symbol = (
            reserve.get("symbol") or
            reserve.get("tokenSymbol") or
            reserve.get("mintSymbol", "???")
        )
        if symbol in ("???", ""):
            return None

        mint = reserve.get("mintAddress") or reserve.get("mint", "")
        state = reserve.get("state") or reserve.get("reserveState") or {}

        # APY extraction — Kamino returns as decimals (0.0682 = 6.82%)
        supply_apy = float(
            state.get("supplyInterestAPY") or
            state.get("supplyApy") or
            reserve.get("supplyInterestAPY") or
            reserve.get("supplyApy", 0)
        ) * 100

        borrow_apy = float(
            state.get("borrowInterestAPY") or
            state.get("borrowApy") or
            reserve.get("borrowInterestAPY") or
            reserve.get("borrowApy", 0)
        ) * 100

        reward_apy = float(
            state.get("rewardApy") or
            reserve.get("rewardApy", 0)
        ) * 100

        tvl_usd = float(
            state.get("totalLiquidityUSD") or
            reserve.get("totalLiquidityUSD") or
            reserve.get("tvl", 0)
        )

        utilization = float(
            state.get("utilizationRatio") or
            reserve.get("utilizationRatio", 0.5)
        ) * 100

        available = float(
            state.get("availableLiquidityUSD") or
            reserve.get("availableLiquidity", tvl_usd * 0.5)
        )

        total_apy = supply_apy + reward_apy
        risk = compute_risk_score(Protocol.KAMINO, tvl_usd, utilization)

        return YieldOpportunity(
            opportunity_id=f"kamino_lend_{mint[:8]}",
            protocol=Protocol.KAMINO,
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
            pool_address=market_addr,
            reward_token="KMNO",
            url=f"https://app.kamino.finance/lending/reserve/{mint}",
        )

    async def _fetch_strategies(self) -> list[YieldOpportunity]:
        """Fetch Kamino strategy vaults (LP/concentrated liquidity)."""
        data = await self._get(STRATEGIES_URL)
        if not data:
            return []

        strategies = data if isinstance(data, list) else data.get("strategies", [])
        opportunities = []

        for s in strategies:
            try:
                opp = self._parse_strategy(s)
                if opp:
                    opportunities.append(opp)
            except Exception as e:
                self.logger.debug(f"Strategy parse error: {e}")

        return opportunities

    def _parse_strategy(self, s: dict) -> YieldOpportunity | None:
        """Parse a Kamino strategy vault."""
        symbol_a = s.get("tokenAMint", {}).get("symbol", "")
        symbol_b = s.get("tokenBMint", {}).get("symbol", "")
        if not symbol_a or not symbol_b:
            return None

        symbol = f"{symbol_a}-{symbol_b}"
        apy = float(s.get("totalApy") or s.get("apy24h") or 0) * 100
        tvl = float(s.get("sharesValueUSD") or s.get("tvl", 0))
        strategy_addr = s.get("strategyPubkey") or s.get("address", "")

        risk = compute_risk_score(Protocol.KAMINO, tvl, 70)

        return YieldOpportunity(
            opportunity_id=f"kamino_vault_{strategy_addr[:8]}",
            protocol=Protocol.KAMINO,
            token_symbol=symbol,
            token_mint=strategy_addr,
            yield_type=YieldType.VAULT,
            supply_apy=apy,
            reward_apy=0.0,
            total_apy=apy,
            borrow_apy=0.0,
            tvl_usd=tvl,
            utilization_pct=70.0,
            available_liquidity_usd=tvl,
            risk_score=risk,
            risk_level=risk_level_from_score(risk),
            pool_address=strategy_addr,
            url=f"https://app.kamino.finance/liquidity/{strategy_addr}",
        )
