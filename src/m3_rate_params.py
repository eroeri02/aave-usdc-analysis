"""M3: read the interest rate model parameters at every daily sample and list when they changed.

Input:  data/usdc_daily.csv (from M2: block, date, utilization, borrow_apr, rate_strategy)
Output: data/usdc_rate_params.csv         one row per sampled block
        data/usdc_rate_param_periods.csv  one row per period with unchanged parameters
"""

from pathlib import Path

import pandas as pd

from aave import get_rate_params, model_borrow_rate
from m2_fetch_history import append_row, blocks_to_fetch, load_done_blocks, sort_csv_by_block

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DAILY_CSV = DATA_DIR / "usdc_daily.csv"
PARAMS_CSV = DATA_DIR / "usdc_rate_params.csv"
PERIODS_CSV = DATA_DIR / "usdc_rate_param_periods.csv"
PARAM_COLUMNS = ["optimal_usage_bps", "base_rate_bps", "slope1_bps", "slope2_bps"]


def fetch_missing_params(daily: pd.DataFrame) -> None:
    """Read the rate parameters for every M2 block that is not yet in PARAMS_CSV."""
    blocks = [int(b) for b in daily["block"]]
    todo = blocks_to_fetch(blocks, load_done_blocks(PARAMS_CSV))
    print(f"{len(blocks)} daily blocks, {len(todo)} to fetch")

    by_block = daily.set_index("block")
    for i, block in enumerate(todo, start=1):
        strategy = by_block.at[block, "rate_strategy"]
        row = {"date": by_block.at[block, "date"], "block": block, "rate_strategy": strategy}
        row |= get_rate_params(strategy, block)
        append_row(PARAMS_CSV, row)
        print(f"[{i}/{len(todo)}] {row['date']}  " + "  ".join(f"{c}={row[c]}" for c in PARAM_COLUMNS))

    if PARAMS_CSV.exists():
        sort_csv_by_block(PARAMS_CSV)


def param_periods(params: pd.DataFrame) -> pd.DataFrame:
    """Collapse daily rows into periods during which all four parameters stayed the same."""
    periods = []
    for row in params.itertuples():
        values = {c: getattr(row, c) for c in PARAM_COLUMNS}
        same_as_previous = periods and all(periods[-1][c] == values[c] for c in PARAM_COLUMNS)
        if same_as_previous:
            periods[-1]["end"] = row.date
            periods[-1]["samples"] += 1
        else:
            periods.append({"start": row.date, "end": row.date, "samples": 1, **values})
    return pd.DataFrame(periods)


def model_errors_bps(daily: pd.DataFrame, params: pd.DataFrame) -> pd.Series:
    """Actual borrow APR minus the model's prediction for each day, in basis points."""
    merged = daily.merge(params[["block"] + PARAM_COLUMNS], on="block")
    predicted = [
        model_borrow_rate(
            row.utilization,
            row.optimal_usage_bps / 10_000,
            row.base_rate_bps / 10_000,
            row.slope1_bps / 10_000,
            row.slope2_bps / 10_000,
        )
        for row in merged.itertuples()
    ]
    return (merged["borrow_apr"] - predicted) * 10_000


def main() -> None:
    daily = pd.read_csv(DAILY_CSV)
    fetch_missing_params(daily)
    params = pd.read_csv(PARAMS_CSV)

    print(f"\nRate strategy contracts used: {params['rate_strategy'].nunique()}")
    print(f"Parameter sources: {params['source'].value_counts().to_dict()}")

    periods = param_periods(params)
    periods.to_csv(PERIODS_CSV, index=False)
    print(f"\n{len(periods)} parameter periods (saved to {PERIODS_CSV.name}):")
    print(periods.to_string(index=False))

    errors = model_errors_bps(daily, params)
    print(
        f"\nModel check over {len(errors)} days: actual - predicted borrow APR, "
        f"median |error| {errors.abs().median():.2f} bps, "
        f"days off by more than 10 bps: {(errors.abs() > 10).sum()}"
    )


if __name__ == "__main__":
    main()
