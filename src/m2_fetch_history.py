"""M2: fetch one Aave v3 USDC snapshot per day (every 7200 blocks) into data/usdc_daily.csv.

Re-running is safe: blocks already in the CSV are skipped, so an interrupted run
continues where it stopped and a later run only adds the new days.
"""

import argparse
import csv
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from aave import get_reserve_data, get_total_supply_usdc, utilization
from rpc import get_block_number, get_block_timestamp

BLOCKS_PER_DAY = 7200  # 86,400 s / 12 s per slot; missed slots make a real day a bit shorter
SECONDS_PER_BLOCK = 12
CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "usdc_daily.csv"


def estimate_block_at(day: date, latest_block: int, latest_timestamp: int) -> int:
    """Rough block number at the start of `day` (UTC), assuming 12 seconds per block."""
    target = datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
    return latest_block - int((latest_timestamp - target) / SECONDS_PER_BLOCK)


def sample_blocks(start_block: int, end_block: int) -> list[int]:
    """All multiples of BLOCKS_PER_DAY from start_block up to end_block (inclusive)."""
    block = math.ceil(start_block / BLOCKS_PER_DAY) * BLOCKS_PER_DAY  # first multiple >= start
    blocks = []
    while block <= end_block:
        blocks.append(block)
        block = block + BLOCKS_PER_DAY
    return blocks


def load_done_blocks(path: Path) -> set[int]:
    """Blocks already saved in the CSV (an empty set if the file does not exist yet)."""
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as f:
        return {int(row["block"]) for row in csv.DictReader(f)}


def blocks_to_fetch(all_blocks: list[int], done_blocks: set[int]) -> list[int]:
    """The blocks of all_blocks that are not in done_blocks, keeping their order."""
    return [block for block in all_blocks if block not in done_blocks]


def fetch_row(block: int) -> dict:
    """Read one daily snapshot of the USDC reserve at `block` (4 RPC calls)."""
    timestamp = get_block_timestamp(block)
    reserve = get_reserve_data(block)
    supplied = get_total_supply_usdc(reserve["a_token"], block)
    borrowed = get_total_supply_usdc(reserve["variable_debt_token"], block)
    return {
        "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
        "block": block,
        "timestamp": timestamp,
        "utilization": utilization(borrowed, supplied),
        "borrow_apr": reserve["borrow_apr"],
        "supply_apr": reserve["supply_apr"],
        "reserve_factor_bps": reserve["reserve_factor_bps"],
        "total_supply_usdc": supplied,
        "total_debt_usdc": borrowed,
        "available_liquidity_usdc": supplied - borrowed,
        "rate_strategy": reserve["rate_strategy"],
    }


def append_row(path: Path, row: dict) -> None:
    """Append one row to the CSV (columns = the row's keys), writing the header if the file is new."""
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def sort_csv_by_block(path: Path) -> None:
    """Rewrite the CSV in block order (rows are appended in fetch order)."""
    pd.read_csv(path).sort_values("block").to_csv(path, index=False)


def parse_args() -> argparse.Namespace:
    default_start = date.today() - timedelta(days=730)
    parser = argparse.ArgumentParser(description="Fetch daily Aave v3 USDC snapshots.")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=default_start,
        help=f"first day to sample, YYYY-MM-DD (default: {default_start})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    latest_block = get_block_number()
    latest_timestamp = get_block_timestamp(latest_block)
    start_block = estimate_block_at(args.start_date, latest_block, latest_timestamp)

    all_blocks = sample_blocks(start_block, latest_block)
    todo = blocks_to_fetch(all_blocks, load_done_blocks(CSV_PATH))
    print(f"{len(all_blocks)} sample blocks since {args.start_date}, {len(todo)} to fetch")

    for i, block in enumerate(todo, start=1):
        row = fetch_row(block)
        append_row(CSV_PATH, row)
        print(
            f"[{i}/{len(todo)}] {row['date']} block {block:,}  "
            f"U={row['utilization']:.2%}  borrow={row['borrow_apr']:.2%}"
        )

    if CSV_PATH.exists():
        sort_csv_by_block(CSV_PATH)
        print(f"Saved {CSV_PATH}")


if __name__ == "__main__":
    main()
