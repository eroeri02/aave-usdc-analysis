"""M4: analysis and charts from the M2 / M3 data.

(a) utilization vs borrow APR, on top of each parameter period's theoretical curve
(b) utilization over time against the kink; share of days above the kink
(c) check the identity supply APR = borrow APR x U x (1 - reserve factor)
(d) stress: days with U > 95% / 98% and the pool's real cash on those days
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MultipleLocator, PercentFormatter

from aave import get_virtual_balance_usdc, model_borrow_rate
from m2_fetch_history import append_row, blocks_to_fetch, load_done_blocks, sort_csv_by_block

ROOT = Path(__file__).resolve().parent.parent
DAILY_CSV = ROOT / "data" / "usdc_daily.csv"
PARAMS_CSV = ROOT / "data" / "usdc_rate_params.csv"
PERIODS_CSV = ROOT / "data" / "usdc_rate_param_periods.csv"
STRESS_CSV = ROOT / "data" / "usdc_stress_days.csv"
CHARTS_DIR = ROOT / "charts"
PARAM_COLUMNS = ["optimal_usage_bps", "base_rate_bps", "slope1_bps", "slope2_bps"]
STRESS_LEVELS = [0.95, 0.98]

# Three regimes, split on the dates slope2 was cut (see data/usdc_rate_param_periods.csv)
REGIMES = [
    ("slope2 60% (Nov - Dec 2024)", "2024-01-01"),
    ("slope2 35% then 20% (Dec 2024 - Oct 2025)", "2024-12-16"),
    ("slope2 ~10% (Oct 2025 - Nov 2026)", "2025-10-03"),
]

# Chart colors (light surface, recessive chrome, three categorical slots)
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans"]  # system sans, with a fallback


# ---------- data ----------


def regime_of(day: pd.Timestamp) -> int:
    """Index into REGIMES for a given day."""
    starts = [pd.Timestamp(start) for _, start in REGIMES]
    return max(i for i, start in enumerate(starts) if day >= start)


def load_data() -> pd.DataFrame:
    """Daily rows (M2) joined with that day's rate parameters (M3)."""
    daily = pd.read_csv(DAILY_CSV)
    params = pd.read_csv(PARAMS_CSV)
    df = daily.merge(params[["block"] + PARAM_COLUMNS], on="block")
    df["date"] = pd.to_datetime(df["date"])
    df["kink"] = df["optimal_usage_bps"] / 10_000
    df["regime"] = df["date"].map(regime_of)
    return df


def load_periods() -> pd.DataFrame:
    periods = pd.read_csv(PERIODS_CSV)
    periods["regime"] = pd.to_datetime(periods["start"]).map(regime_of)
    return periods


def rate_curve(period, utilizations: list[float]) -> list[float]:
    """Theoretical borrow APR of one parameter period at each utilization."""
    return [
        model_borrow_rate(
            u,
            period.optimal_usage_bps / 10_000,
            period.base_rate_bps / 10_000,
            period.slope1_bps / 10_000,
            period.slope2_bps / 10_000,
        )
        for u in utilizations
    ]


# ---------- analysis ----------


def share_of_days_above_kink(df: pd.DataFrame) -> float:
    """Fraction of days (0 to 1) on which utilization was above that day's kink."""
    # Same result with an explicit loop (my first version):
    # more_than_kink = 0
    # for row in df.itertuples():
    #     if row.utilization > row.kink:
    #         more_than_kink = more_than_kink + 1
    # return more_than_kink / len(df)

    # Compare the two columns day by day (True/False); the mean of booleans is the share of True.
    return (df["utilization"] > df["kink"]).mean()


def predicted_supply_apr(df: pd.DataFrame) -> pd.Series:
    """Supply APR implied by the identity: borrow APR x U x (1 - reserve factor)."""
    # Column arithmetic runs row by row; reserve_factor_bps is in basis points (1000 = 10%).
    calculated_supply_apr = df["borrow_apr"] * df["utilization"] * (1 - df["reserve_factor_bps"] / 10_000)
    return calculated_supply_apr


def fetch_stress_cash(df: pd.DataFrame) -> pd.DataFrame:
    """Real pool cash on every day with U above the lowest stress level (cached in a CSV)."""
    stress = df[df["utilization"] > STRESS_LEVELS[0]].set_index("block")
    todo = blocks_to_fetch([int(b) for b in stress.index], load_done_blocks(STRESS_CSV))
    for block in todo:
        day = stress.loc[block]
        append_row(
            STRESS_CSV,
            {
                "date": day["date"].date().isoformat(),
                "block": block,
                "utilization": day["utilization"],
                "borrow_apr": day["borrow_apr"],
                "supply_minus_debt_usdc": day["available_liquidity_usdc"],
                "cash_usdc": get_virtual_balance_usdc(block),
            },
        )
    if not STRESS_CSV.exists():
        return pd.DataFrame()
    sort_csv_by_block(STRESS_CSV)
    return pd.read_csv(STRESS_CSV, parse_dates=["date"])


# ---------- charts ----------


def new_chart(title: str, subtitle: str):
    """A figure with the project's chart style: light surface, hairline grid, left-aligned titles."""
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=AXIS, labelcolor=INK_2, labelsize=9)
    fig.text(0.075, 0.95, title, fontsize=13, fontweight="semibold", color=INK)
    fig.text(0.075, 0.905, subtitle, fontsize=9.5, color=INK_2)
    fig.subplots_adjust(left=0.075, right=0.97, top=0.85, bottom=0.11)
    return fig, ax


def style_legend(ax) -> None:
    legend = ax.legend(loc="upper left", frameon=False, fontsize=9)
    for text in legend.get_texts():
        text.set_color(INK_2)


def format_date_axis(ax) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


def save(fig, name: str) -> None:
    CHARTS_DIR.mkdir(exist_ok=True)
    fig.savefig(CHARTS_DIR / name, facecolor=SURFACE)
    plt.close(fig)
    print(f"  saved charts/{name}")


def chart_rate_curve(df: pd.DataFrame, periods: pd.DataFrame) -> None:
    """(a) Daily (utilization, borrow APR) points over the theoretical curves."""
    fig, ax = new_chart(
        "Borrow APR sits exactly on the kinked rate curve",
        f"Each dot is one day. Grey: curves of all {len(periods)} parameter periods. "
        "Colored: the longest period in each regime.",
    )
    utilizations = [i / 1000 for i in range(450, 1001)]
    for period in periods.itertuples():
        ax.plot(utilizations, rate_curve(period, utilizations), color=AXIS, linewidth=0.6, zorder=1)
    for i, (label, _) in enumerate(REGIMES):
        longest = periods[periods["regime"] == i].sort_values("samples").iloc[-1]
        ax.plot(utilizations, rate_curve(longest, utilizations), color=SERIES[i], linewidth=2, zorder=2)
        days = df[df["regime"] == i]
        ax.scatter(
            days["utilization"], days["borrow_apr"], s=24, color=SERIES[i],
            edgecolor=SURFACE, linewidth=0.6, label=label, zorder=3,
        )
    peak = df.loc[df["borrow_apr"].idxmax()]
    ax.annotate(
        f"{peak['date']:%d %b %Y}: {peak['borrow_apr']:.1%} at U = {peak['utilization']:.1%}",
        xy=(peak["utilization"], peak["borrow_apr"]), xytext=(0.47, 0.215),
        fontsize=9, color=INK_2, arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8},
    )
    ax.set_xlim(0.45, 1.005)
    ax.set_ylim(0, 0.30)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Utilization", color=INK_2, fontsize=9)
    ax.set_ylabel("Borrow APR", color=INK_2, fontsize=9)
    style_legend(ax)
    save(fig, "a_rate_curve.png")


def chart_utilization(df: pd.DataFrame, share_above: float) -> None:
    """(b) Utilization over time with the kink as a step line."""
    fig, ax = new_chart(
        f"Utilization was above the kink on {share_above:.0%} of days",
        "Daily utilization of Aave v3 USDC (Ethereum) and the kink set by governance.",
    )
    above = df["utilization"] > df["kink"]
    ax.fill_between(
        df["date"], df["kink"], df["utilization"], where=above, interpolate=True,
        color=SERIES[1], alpha=0.45, linewidth=0, label="Above the kink",
    )
    ax.plot(df["date"], df["utilization"], color=SERIES[0], linewidth=1.5, label="Utilization")
    ax.step(df["date"], df["kink"], where="post", color=INK_2, linewidth=1.2, label="Kink (optimal usage)")
    ax.annotate(
        "19-22 Apr 2026: U = 100%,\npool cash about $0",
        xy=(pd.Timestamp("2026-04-20"), 1.0), xytext=(pd.Timestamp("2025-09-01"), 1.035),
        fontsize=9, color=INK_2, arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8},
    )
    ax.set_ylim(0.5, 1.06)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    format_date_axis(ax)
    style_legend(ax)
    save(fig, "b_utilization_vs_kink.png")


def chart_supply_identity(df: pd.DataFrame, gap_bps: pd.Series) -> None:
    """(c) Actual supply APR minus the identity's prediction, in basis points."""
    fig, ax = new_chart(
        "Supply APR = borrow APR x U x (1 - reserve factor) holds every day",
        f"Actual minus identity, in basis points (1 bp = 0.01%). Median |gap| "
        f"{gap_bps.abs().median():.2f} bp, largest {gap_bps.abs().max():.2f} bp.",
    )
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.plot(df["date"], gap_bps, color=SERIES[0], linewidth=1.2)
    ax.set_ylabel("Gap (bp)", color=INK_2, fontsize=9)
    format_date_axis(ax)
    save(fig, "c_supply_identity.png")


def chart_liquidity(df: pd.DataFrame, stress: pd.DataFrame) -> None:
    """(d) Withdrawable cash over time; stress days marked with the pool's real cash."""
    fig, ax = new_chart(
        "Withdrawable cash hit zero in April 2026",
        "Blue: supply minus debt. Orange: days with U > 95%, at the pool's real cash "
        "(virtual balance).",
    )
    ax.plot(df["date"], df["available_liquidity_usdc"], color=SERIES[0], linewidth=1.5, label="Supply - debt")
    ax.scatter(
        stress["date"], stress["cash_usdc"], s=30, color=SERIES[1], edgecolor=SURFACE,
        linewidth=0.8, zorder=3, label="U > 95%: real pool cash",
    )
    worst = stress.loc[stress["cash_usdc"].idxmin()]
    ax.annotate(
        f"{worst['date']:%d %b %Y}: ${worst['cash_usdc']:,.0f} left",
        xy=(worst["date"], worst["cash_usdc"]), xytext=(pd.Timestamp("2026-05-20"), 0.42e9),
        fontsize=9, color=INK_2, arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8},
    )
    ax.set_ylim(bottom=-0.05e9)
    ax.yaxis.set_major_locator(MultipleLocator(0.5e9))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v / 1e9:.1f}B"))
    format_date_axis(ax)
    style_legend(ax)
    save(fig, "d_withdrawable_cash.png")


# ---------- main ----------


def main() -> None:
    df = load_data()
    periods = load_periods()
    print(f"{len(df)} days, {df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}\n")

    share_above = share_of_days_above_kink(df)
    print(f"(b) days above the kink: {share_above:.1%}")
    for i, (label, _) in enumerate(REGIMES):
        print(f"    {label:<45} {share_of_days_above_kink(df[df['regime'] == i]):.1%}")

    gap_bps = (df["supply_apr"] - predicted_supply_apr(df)) * 10_000
    print(f"\n(c) supply identity gap: median |gap| {gap_bps.abs().median():.3f} bp, "
          f"max {gap_bps.abs().max():.3f} bp")

    stress = fetch_stress_cash(df)
    print("\n(d) stress days")
    for level in STRESS_LEVELS:
        print(f"    U > {level:.0%}: {(df['utilization'] > level).sum()} days")
    worst = stress.loc[stress["cash_usdc"].idxmin()]
    print(f"    lowest real cash: ${worst['cash_usdc']:,.0f} on {worst['date']:%Y-%m-%d} "
          f"(U {worst['utilization']:.3%}, borrow APR {worst['borrow_apr']:.2%})")
    print(stress[["date", "utilization", "borrow_apr", "cash_usdc"]].to_string(index=False))

    print("\nCharts:")
    chart_rate_curve(df, periods)
    chart_utilization(df, share_above)
    chart_supply_identity(df, gap_bps)
    chart_liquidity(df, stress)


if __name__ == "__main__":
    main()
