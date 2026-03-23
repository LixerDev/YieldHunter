"""
Dashboard — Rich terminal display for YieldHunter.
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from src.models import (
    YieldOpportunity, AllocationPlan, Protocol, RiskLevel,
    PROTOCOL_COLORS, YieldType
)
from config import config

console = Console()

RISK_COLORS = {
    RiskLevel.LOW:    "green",
    RiskLevel.MEDIUM: "yellow",
    RiskLevel.HIGH:   "red",
}

YIELD_TYPE_ICONS = {
    YieldType.SUPPLY: "",
    YieldType.BORROW: "↑",
    YieldType.LP:     "♦",
    YieldType.VAULT:  "⬡",
}


def _fmt_apy(apy: float) -> str:
    color = "bright_green" if apy >= 8 else "green" if apy >= 5 else "yellow" if apy >= 2 else "dim"
    suffix = " 🔥" if apy >= 8 else ""
    return f"[{color}]{apy:.2f}%{suffix}[/{color}]"


def _fmt_tvl(tvl: float) -> str:
    if tvl >= 1e9:
        return f"${tvl/1e9:.2f}B"
    if tvl >= 1e6:
        return f"${tvl/1e6:.1f}M"
    if tvl >= 1e3:
        return f"${tvl/1e3:.1f}K"
    return f"${tvl:.0f}"


def render_top(
    opportunities: list[YieldOpportunity],
    title: str = "Top Yield Opportunities",
    protocols_active: int = 4,
):
    """Render a ranked table of yield opportunities."""
    now = datetime.utcnow().strftime("%H:%M:%S UTC")
    console.clear()
    console.rule(
        f"[bold]🌾 YieldHunter[/bold]  [dim]{protocols_active} protocols  |  {now}[/dim]"
    )
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=True)
    table.add_column("#", width=4, style="dim")
    table.add_column("Token", width=12, style="bold")
    table.add_column("Protocol", width=12)
    table.add_column("Type", width=8)
    table.add_column("Supply APY", justify="right", width=12)
    table.add_column("Reward APY", justify="right", width=12)
    table.add_column("Total APY", justify="right", width=14)
    table.add_column("TVL", justify="right", width=10)
    table.add_column("Util%", justify="right", width=7)
    table.add_column("Risk", width=8)

    for i, opp in enumerate(opportunities, 1):
        proto_color = PROTOCOL_COLORS.get(opp.protocol, "white")
        risk_color = RISK_COLORS.get(opp.risk_level, "white")
        type_icon = YIELD_TYPE_ICONS.get(opp.yield_type, "")

        util_color = (
            "green" if 40 <= opp.utilization_pct <= 80
            else "red" if opp.utilization_pct > 90
            else "yellow"
        )

        table.add_row(
            str(i),
            opp.token_symbol[:12],
            f"[{proto_color}]{opp.protocol.value}[/{proto_color}]",
            f"[dim]{type_icon} {opp.yield_type.value}[/dim]",
            f"[dim]{opp.supply_apy:.2f}%[/dim]",
            f"[cyan]+{opp.reward_apy:.2f}%[/cyan]" if opp.reward_apy > 0 else "[dim]—[/dim]",
            _fmt_apy(opp.total_apy),
            _fmt_tvl(opp.tvl_usd),
            f"[{util_color}]{opp.utilization_pct:.1f}%[/{util_color}]",
            f"[{risk_color}]{opp.risk_level.value}[/{risk_color}]",
        )

    console.print(table)

    # Summary footer
    if opportunities:
        best = opportunities[0]
        proto_color = PROTOCOL_COLORS.get(best.protocol, "white")
        console.print(
            f"  [dim]{len(opportunities)} opportunities  |  "
            f"Best: [{proto_color}]{best.total_apy:.2f}%[/{proto_color}] "
            f"({best.token_symbol} / {best.protocol.value})[/dim]\n"
        )


def render_compare(opportunities: list[YieldOpportunity], token: str):
    """Render a comparison of one token across all protocols."""
    console.print(f"\n[bold]📊 {token} Yield Comparison Across All Protocols[/bold]\n")

    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
    table.add_column("Protocol", style="bold", width=14)
    table.add_column("Supply APY", justify="right")
    table.add_column("Reward APY", justify="right")
    table.add_column("Total APY", justify="right")
    table.add_column("Borrow APY", justify="right")
    table.add_column("TVL", justify="right")
    table.add_column("Util%", justify="right")
    table.add_column("Risk", justify="center")

    for i, opp in enumerate(opportunities):
        proto_color = PROTOCOL_COLORS.get(opp.protocol, "white")
        risk_color = RISK_COLORS.get(opp.risk_level, "white")
        best_mark = " ⭐" if i == 0 else ""

        table.add_row(
            f"[{proto_color}]{opp.protocol.value}{best_mark}[/{proto_color}]",
            f"{opp.supply_apy:.2f}%",
            f"[cyan]+{opp.reward_apy:.2f}%[/cyan]" if opp.reward_apy > 0 else "—",
            _fmt_apy(opp.total_apy),
            f"[dim]{opp.borrow_apy:.2f}%[/dim]",
            _fmt_tvl(opp.tvl_usd),
            f"{opp.utilization_pct:.1f}%",
            f"[{risk_color}]{opp.risk_level.value}[/{risk_color}]",
        )

    console.print(table)


def render_allocation(plan: AllocationPlan):
    """Render a capital allocation plan."""
    console.print(f"\n[bold]💡 Optimal Allocation — ${plan.total_capital:,.2f}[/bold]\n")

    table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
    table.add_column("Protocol", style="bold", width=12)
    table.add_column("Token", width=10)
    table.add_column("APY", justify="right")
    table.add_column("Allocation", justify="right")
    table.add_column("% of Total", justify="right")
    table.add_column("Weekly Yield", justify="right")
    table.add_column("Annual Yield", justify="right")
    table.add_column("Risk", width=8)

    for s in plan.slices:
        opp = s.opportunity
        proto_color = PROTOCOL_COLORS.get(opp.protocol, "white")
        risk_color = RISK_COLORS.get(opp.risk_level, "white")

        table.add_row(
            f"[{proto_color}]{opp.protocol.value}[/{proto_color}]",
            opp.token_symbol,
            _fmt_apy(opp.total_apy),
            f"${s.amount_usd:,.2f}",
            f"{s.pct_of_total:.1f}%",
            f"[green]${s.weekly_yield:,.2f}[/green]",
            f"[green]${s.annual_yield:,.2f}[/green]",
            f"[{risk_color}]{opp.risk_level.value}[/{risk_color}]",
        )

    # Totals row
    console.print(table)
    console.print(
        f"  [bold]Blended APY:[/bold] [bright_green]{plan.blended_apy:.2f}%[/bright_green]  |  "
        f"[bold]Weekly:[/bold] [green]${plan.total_weekly_yield:,.2f}[/green]  |  "
        f"[bold]Annual:[/bold] [green]${plan.total_annual_yield:,.2f}[/green]\n"
    )
