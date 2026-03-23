"""
Alerter — Discord alerts for APY changes and new high-yield opportunities.
"""

import aiohttp
import time
from src.models import YieldOpportunity, Protocol, PROTOCOL_COLORS
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

_last_alert: dict[str, float] = {}
_last_apys:  dict[str, float] = {}


class Alerter:
    def __init__(self):
        self.webhook = config.DISCORD_WEBHOOK_URL
        self.cooldown = config.ALERT_COOLDOWN_MINUTES * 60

    def _should_alert(self, key: str) -> bool:
        return (time.time() - _last_alert.get(key, 0)) > self.cooldown

    def _record(self, key: str):
        _last_alert[key] = time.time()

    async def check_and_alert(self, opportunities: list[YieldOpportunity]):
        """
        Check all opportunities for alert conditions:
        1. New high-yield opportunity (APY > threshold)
        2. Significant APY drop vs previous scan
        """
        if not self.webhook:
            return

        for opp in opportunities:
            key = opp.opportunity_id
            prev_apy = _last_apys.get(key)

            # New high-yield opportunity
            if (opp.total_apy >= config.ALERT_NEW_OPPORTUNITY_APY
                    and prev_apy is None
                    and self._should_alert(f"new_{key}")):
                await self._send_new_opportunity(opp)
                self._record(f"new_{key}")

            # APY drop alert
            if (prev_apy is not None
                    and (prev_apy - opp.total_apy) >= config.ALERT_APY_DROP_PCT
                    and self._should_alert(f"drop_{key}")):
                await self._send_apy_drop(opp, prev_apy)
                self._record(f"drop_{key}")

            _last_apys[key] = opp.total_apy

    async def _send_new_opportunity(self, opp: YieldOpportunity):
        embed = {
            "title": f"🔥 NEW HIGH-YIELD OPPORTUNITY — {opp.token_symbol}",
            "color": 0x00FF88,
            "fields": [
                {"name": "Protocol", "value": opp.protocol.value, "inline": True},
                {"name": "Token", "value": opp.token_symbol, "inline": True},
                {"name": "Type", "value": opp.yield_type.value, "inline": True},
                {"name": "Supply APY", "value": f"{opp.supply_apy:.2f}%", "inline": True},
                {"name": "Reward APY", "value": f"+{opp.reward_apy:.2f}%", "inline": True},
                {"name": "Total APY", "value": f"**{opp.total_apy:.2f}%**", "inline": True},
                {"name": "TVL", "value": f"${opp.tvl_usd:,.0f}", "inline": True},
                {"name": "Risk", "value": opp.risk_level.value, "inline": True},
                {"name": "URL", "value": opp.url or "N/A", "inline": False},
            ],
            "footer": {"text": "YieldHunter by LixerDev • Solana DeFi Yield Aggregator"},
        }
        await self._send(embed)

    async def _send_apy_drop(self, opp: YieldOpportunity, prev_apy: float):
        drop = prev_apy - opp.total_apy
        embed = {
            "title": f"⚠️ APY DROP — {opp.protocol.value} {opp.token_symbol}",
            "color": 0xFF4444,
            "fields": [
                {"name": "Protocol", "value": opp.protocol.value, "inline": True},
                {"name": "Token", "value": opp.token_symbol, "inline": True},
                {"name": "Previous APY", "value": f"{prev_apy:.2f}%", "inline": True},
                {"name": "Current APY", "value": f"{opp.total_apy:.2f}%", "inline": True},
                {"name": "Drop", "value": f"-{drop:.2f}%", "inline": True},
            ],
            "footer": {"text": "YieldHunter by LixerDev"},
        }
        await self._send(embed)

    async def _send(self, embed: dict):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook,
                    json={"embeds": [embed]},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status in (200, 204):
                        logger.info("Discord alert sent")
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")
