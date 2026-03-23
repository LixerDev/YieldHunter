#!/usr/bin/env python3
"""
YieldHunter — Solana DeFi Yield Aggregator
Compares APY across Kamino, MarginFi, Solend, and Drift.
Built by LixerDev
"""

import asyncio
import json
from typing import Optional
import typer
from rich.console import Console

from config import config
from src.logger import get_logger, print_banner
from src.aggregator import Aggregator
from src.ranker import Ranker
from src.optimizer import Optimizer
from src.alerter import Alerter
from src.dashboard import render_top, render_compare, render_allocation

app = typer.Typer(
    help="YieldHunter — Real-time DeFi yield aggregator for Solana",
    no_args_is_help=True
)
console = Console()
logger = get_logger(__name__)


@app.command()
def top(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Filter by token symbol"),
    protocol: Optional[str] = typer.Option(None, "--protocol", "-p", help="Filter by protocol"),
    min_apy: Optional[float] = typer.Option(None, "--min-apy", help="Minimum APY %"),
    risk: Optional[str] = typer.Option(None, "--risk", "-r", help="Risk level: low, medium, high"),
    sort: str = typer.Option("apy", "--sort", "-s", help="Sort by: apy, risk_adjusted, tvl"),
    limit: int = typer.Option(15, "--limit", "-n", help="Number of results"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export JSON"),
    protocols: Optional[str] = typer.Option(None, "--protocols", help="Comma-separated protocol list"),
):
    """Show top yield opportunities across all protocols."""
    print_banner()

    async def _run():
        proto_list = protocols.split(",") if protocols else None
        aggregator = Aggregator(proto_list)
        ranker = Ranker()
        alerter = Alerter()

        console.print("[dim]Fetching live APY data...[/dim]")
        all_opps = await aggregator.fetch_all()

        await alerter.check_and_alert(all_opps)

        ranked = ranker.rank(
            all_opps,
            sort_by=sort,
            token=token,
            protocol=protocol,
            risk_level=risk,
            min_apy=min_apy,
            limit=limit,
        )

        render_top(ranked, protocols_active=len(aggregator.protocols_used()))

        if output:
            data = [o.to_dict() for o in ranked]
            with open(output, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[dim]Exported to {output}[/dim]")

    asyncio.run(_run())


@app.command()
def compare(
    token: str = typer.Argument(..., help="Token symbol to compare (e.g. USDC, SOL, JUP)"),
    protocols: Optional[str] = typer.Option(None, "--protocols", help="Comma-separated protocol list"),
):
    """Compare a specific token's APY across all protocols."""
    print_banner()

    async def _run():
        proto_list = protocols.split(",") if protocols else None
        aggregator = Aggregator(proto_list)
        ranker = Ranker()

        console.print(f"[dim]Fetching {token} yield data across all protocols...[/dim]")
        all_opps = await aggregator.fetch_all()
        token_opps = ranker.compare_token(all_opps, token)

        if not token_opps:
            console.print(f"[yellow]No yield opportunities found for {token}.[/yellow]")
            console.print("[dim]Check the token symbol or try a different one.[/dim]")
            return

        render_compare(token_opps, token)

    asyncio.run(_run())


@app.command()
def optimize(
    capital: float = typer.Option(10000.0, "--capital", "-c", help="Capital to allocate (USD)"),
    max_protocol_pct: float = typer.Option(40.0, "--max-per-protocol", help="Max % per protocol"),
    max_token_pct: float = typer.Option(60.0, "--max-per-token", help="Max % per token"),
    min_position: float = typer.Option(500.0, "--min-position", help="Minimum position size (USD)"),
    max_risk: Optional[str] = typer.Option(None, "--max-risk", help="Max risk level: low, medium, high"),
    max_positions: int = typer.Option(6, "--max-positions", help="Max number of positions"),
    protocols: Optional[str] = typer.Option(None, "--protocols", help="Comma-separated protocol list"),
):
    """Compute optimal capital allocation for maximum risk-adjusted yield."""
    print_banner()

    async def _run():
        proto_list = protocols.split(",") if protocols else None
        aggregator = Aggregator(proto_list)
        optimizer = Optimizer()

        console.print(f"[dim]Fetching all yield data for ${capital:,.2f} optimization...[/dim]")
        all_opps = await aggregator.fetch_all()

        plan = optimizer.optimize(
            all_opps,
            capital=capital,
            max_per_protocol_pct=max_protocol_pct,
            max_per_token_pct=max_token_pct,
            min_position_usd=min_position,
            max_risk=max_risk,
            max_positions=max_positions,
        )

        render_allocation(plan)

    asyncio.run(_run())


@app.command()
def watch(
    token: Optional[str] = typer.Option(None, "--token", "-t"),
    min_apy: Optional[float] = typer.Option(None, "--min-apy"),
    risk: Optional[str] = typer.Option(None, "--risk"),
    sort: str = typer.Option("apy", "--sort"),
    limit: int = typer.Option(15, "--limit"),
    interval: Optional[int] = typer.Option(None, "--interval", "-i", help="Refresh interval (seconds)"),
):
    """Live dashboard — refreshes automatically every N seconds."""
    print_banner()

    if interval:
        config.REFRESH_INTERVAL = interval

    async def _loop():
        aggregator = Aggregator()
        ranker = Ranker()
        alerter = Alerter()

        console.print(
            f"[dim]Starting live watch  |  refresh: {config.REFRESH_INTERVAL}s  |  "
            "Press Ctrl+C to stop[/dim]\n"
        )

        while True:
            try:
                all_opps = await aggregator.fetch_all()
                await alerter.check_and_alert(all_opps)
                ranked = ranker.rank(
                    all_opps,
                    sort_by=sort,
                    token=token,
                    risk_level=risk,
                    min_apy=min_apy,
                    limit=limit,
                )
                render_top(ranked, protocols_active=len(aggregator.protocols_used()))
                await asyncio.sleep(config.REFRESH_INTERVAL)
            except KeyboardInterrupt:
                console.print("\n[dim]Watch stopped.[/dim]")
                break
            except Exception as e:
                logger.error(f"Watch loop error: {e}")
                await asyncio.sleep(10)

    asyncio.run(_loop())


@app.command()
def protocols():
    """List all supported protocols."""
    from rich.table import Table
    from rich import box as rbox
    from src.models import Protocol, PROTOCOL_COLORS

    print_banner()
    table = Table(box=rbox.ROUNDED, title="Supported Protocols")
    table.add_column("Protocol", style="bold")
    table.add_column("Products")
    table.add_column("Reward Token")
    table.add_column("URL")

    data = [
        (Protocol.KAMINO,   "Lending + LP Vaults",   "KMNO",  "https://app.kamino.finance"),
        (Protocol.MARGINFI, "Lending Markets",        "MRGN",  "https://app.marginfi.com"),
        (Protocol.SOLEND,   "Lending Markets",        "SLND",  "https://solend.fi"),
        (Protocol.DRIFT,    "Lending + Perps",        "DRIFT", "https://app.drift.trade"),
    ]

    for proto, products, reward, url in data:
        color = PROTOCOL_COLORS.get(proto, "white")
        table.add_row(
            f"[{color}]{proto.value}[/{color}]",
            products, reward, f"[dim]{url}[/dim]"
        )

    console.print(table)


if __name__ == "__main__":
    app()
