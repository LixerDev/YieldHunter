"""
Aggregator — fetches from all protocols concurrently and merges results.
"""

import asyncio
from src.models import YieldOpportunity, Protocol
from src.protocols.kamino import KaminoFetcher
from src.protocols.marginfi import MarginFiFetcher
from src.protocols.solend import SolendFetcher
from src.protocols.drift import DriftFetcher
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

ALL_FETCHERS = [
    KaminoFetcher,
    MarginFiFetcher,
    SolendFetcher,
    DriftFetcher,
]


class Aggregator:
    def __init__(self, protocols: list[str] = None):
        """
        Initialize the aggregator.

        Parameters:
        - protocols: Optional list of protocol names to include.
          If None, all protocols are fetched.
        """
        self._fetchers = []
        for cls in ALL_FETCHERS:
            if protocols is None or cls.protocol.value.lower() in [p.lower() for p in protocols]:
                self._fetchers.append(cls())

    async def fetch_all(self) -> list[YieldOpportunity]:
        """
        Fetch opportunities from all protocols concurrently.

        Returns:
        - list[YieldOpportunity]: All valid opportunities, filtered by min TVL.
        """
        tasks = [fetcher.fetch() for fetcher in self._fetchers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_opps: list[YieldOpportunity] = []
        for i, result in enumerate(results):
            fetcher_name = self._fetchers[i].protocol.value
            if isinstance(result, Exception):
                logger.error(f"{fetcher_name} fetch failed: {result}")
                continue
            if isinstance(result, list):
                valid = [
                    o for o in result
                    if o.tvl_usd >= config.MIN_TVL_USD
                    and o.total_apy >= config.MIN_APY_PCT
                ]
                logger.info(f"{fetcher_name}: {len(valid)} valid / {len(result)} total")
                all_opps.extend(valid)

        logger.info(f"Total opportunities aggregated: {len(all_opps)}")
        return all_opps

    def protocols_used(self) -> list[str]:
        return [f.protocol.value for f in self._fetchers]
