"""
Optimizer — recommends capital allocation across DeFi protocols.

Algorithm:
1. Rank opportunities by risk-adjusted APY
2. Greedy allocation: fill highest APY first
3. Constraints:
   - Max X% in any single protocol
   - Max Y% in any single token
   - Min position size per allocation
   - Risk level filter

Result: AllocationPlan with blended APY and per-position breakdown.
"""

from src.models import YieldOpportunity, AllocationSlice, AllocationPlan, RiskLevel
from src.ranker import Ranker
from src.logger import get_logger
from config import config

logger = get_logger(__name__)


class Optimizer:
    def __init__(self):
        self.ranker = Ranker()

    def optimize(
        self,
        opportunities: list[YieldOpportunity],
        capital: float,
        max_per_protocol_pct: float = None,
        max_per_token_pct: float = None,
        min_position_usd: float = None,
        max_risk: str = None,
        max_positions: int = 6,
    ) -> AllocationPlan:
        """
        Compute the optimal capital allocation across opportunities.

        Parameters:
        - opportunities: All available yield opportunities
        - capital: Total capital to allocate (USD)
        - max_per_protocol_pct: Max % in one protocol (default from config)
        - max_per_token_pct: Max % in one token (default from config)
        - min_position_usd: Minimum per position (default from config)
        - max_risk: Maximum risk level ('low', 'medium', 'high')
        - max_positions: Maximum number of positions

        Returns:
        - AllocationPlan with recommended slices
        """
        max_proto_pct = max_per_protocol_pct or config.MAX_PER_PROTOCOL_PCT
        max_token_pct = max_per_token_pct or config.MAX_PER_TOKEN_PCT
        min_pos = min_position_usd or config.MIN_POSITION_USD

        # Filter by risk
        filtered = list(opportunities)
        if max_risk:
            risk_order = {"low": 0, "medium": 1, "high": 2}
            max_risk_idx = risk_order.get(max_risk.lower(), 2)
            filtered = [
                o for o in filtered
                if risk_order.get(o.risk_level.value.lower(), 2) <= max_risk_idx
            ]

        # Sort by risk-adjusted APY
        ranked = self.ranker.rank(filtered, sort_by="risk_adjusted")
        if not ranked:
            logger.warning("No opportunities found for optimization")
            return AllocationPlan(total_capital=capital)

        plan = AllocationPlan(total_capital=capital)
        remaining = capital
        protocol_allocated: dict[str, float] = {}
        token_allocated: dict[str, float] = {}

        for opp in ranked:
            if remaining < min_pos:
                break
            if len(plan.slices) >= max_positions:
                break

            proto_key = opp.protocol.value
            token_key = opp.token_symbol.upper()

            # Check protocol cap
            proto_current = protocol_allocated.get(proto_key, 0.0)
            proto_max_usd = capital * max_proto_pct / 100
            proto_space = proto_max_usd - proto_current

            # Check token cap
            token_current = token_allocated.get(token_key, 0.0)
            token_max_usd = capital * max_token_pct / 100
            token_space = token_max_usd - token_current

            # How much can we put here?
            can_allocate = min(remaining, proto_space, token_space)
            can_allocate = max(0, can_allocate)

            if can_allocate < min_pos:
                continue

            # Allocate!
            protocol_allocated[proto_key] = proto_current + can_allocate
            token_allocated[token_key] = token_current + can_allocate
            remaining -= can_allocate

            slice_ = AllocationSlice(
                opportunity=opp,
                amount_usd=can_allocate,
                pct_of_total=(can_allocate / capital) * 100,
            )
            plan.slices.append(slice_)

        logger.info(
            f"Optimization complete: {len(plan.slices)} positions, "
            f"blended APY {plan.blended_apy:.2f}%, "
            f"annual yield ${plan.total_annual_yield:,.2f}"
        )
        return plan
