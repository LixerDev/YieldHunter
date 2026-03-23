"""
Ranker — sorts and filters yield opportunities.

Supports multiple sort keys:
- total_apy: raw APY (highest first)
- risk_adjusted: APY after risk penalty
- tvl: total value locked (safest/largest first)
- utilization: ideal utilization (40–80%)
"""

from src.models import YieldOpportunity, RiskLevel


SORT_KEYS = {
    "apy":          lambda o: -o.total_apy,
    "risk_adjusted": lambda o: -o.risk_adjusted_apy,
    "tvl":          lambda o: -o.tvl_usd,
    "utilization":  lambda o: abs(o.utilization_pct - 60),  # Closest to 60%
    "supply_apy":   lambda o: -o.supply_apy,
    "reward_apy":   lambda o: -o.reward_apy,
}


class Ranker:
    def rank(
        self,
        opportunities: list[YieldOpportunity],
        sort_by: str = "apy",
        token: str = None,
        protocol: str = None,
        risk_level: str = None,
        yield_type: str = None,
        min_apy: float = None,
        max_risk_score: float = None,
        limit: int = None,
    ) -> list[YieldOpportunity]:
        """
        Filter and sort yield opportunities.

        Parameters:
        - opportunities: All fetched opportunities
        - sort_by: Sort key — apy, risk_adjusted, tvl, utilization
        - token: Filter by token symbol (case-insensitive)
        - protocol: Filter by protocol name
        - risk_level: Filter by risk level (low, medium, high)
        - yield_type: Filter by type (supply, borrow, lp, vault)
        - min_apy: Minimum total APY
        - max_risk_score: Maximum risk score (0–100)
        - limit: Max number of results

        Returns:
        - Ranked list of YieldOpportunity
        """
        filtered = list(opportunities)

        if token:
            token_upper = token.upper()
            filtered = [
                o for o in filtered
                if token_upper in o.token_symbol.upper()
            ]

        if protocol:
            proto_lower = protocol.lower()
            filtered = [
                o for o in filtered
                if proto_lower in o.protocol.value.lower()
            ]

        if risk_level:
            rl = RiskLevel(risk_level.upper())
            filtered = [o for o in filtered if o.risk_level == rl]

        if yield_type:
            yt_lower = yield_type.lower()
            filtered = [o for o in filtered if o.yield_type.value.lower() == yt_lower]

        if min_apy is not None:
            filtered = [o for o in filtered if o.total_apy >= min_apy]

        if max_risk_score is not None:
            filtered = [o for o in filtered if o.risk_score <= max_risk_score]

        sort_fn = SORT_KEYS.get(sort_by, SORT_KEYS["apy"])
        filtered.sort(key=sort_fn)

        if limit:
            filtered = filtered[:limit]

        return filtered

    def compare_token(
        self, opportunities: list[YieldOpportunity], token: str
    ) -> list[YieldOpportunity]:
        """Get all opportunities for a specific token across all protocols."""
        token_upper = token.upper()
        filtered = [o for o in opportunities if token_upper in o.token_symbol.upper()]
        return sorted(filtered, key=lambda o: -o.total_apy)

    def top_per_protocol(
        self, opportunities: list[YieldOpportunity], n: int = 3
    ) -> dict[str, list[YieldOpportunity]]:
        """Get top N opportunities per protocol."""
        result = {}
        for opp in opportunities:
            key = opp.protocol.value
            if key not in result:
                result[key] = []
            result[key].append(opp)

        for key in result:
            result[key] = sorted(result[key], key=lambda o: -o.total_apy)[:n]

        return result
