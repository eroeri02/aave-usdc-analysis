"""M1: snapshot of the Aave v3 USDC reserve, at a reference block and at the latest block."""

from abi import function_selector
from aave import get_reserve_data, get_total_supply_usdc, utilization
from rpc import get_block_number

# Selectors from the project notes; check_selectors() re-derives them with keccak256.
EXPECTED_SELECTORS = {
    "getReserveData(address)": "0x35ea6a75",
    "totalSupply()": "0x18160ddd",
}

# Values noted by hand on 23 Nov 2026 at this block, used as a sanity check.
REFERENCE_BLOCK = 26_475_412
REFERENCE_VALUES = "U ~75.5%, borrow APR ~3.70%, supply APR ~2.51%, RF 1000 bps, supply ~4.16B, debt ~3.14B"


def check_selectors() -> None:
    """Print each selector computed from its signature next to the expected one."""
    for signature, expected in EXPECTED_SELECTORS.items():
        computed = function_selector(signature)
        status = "OK" if computed == expected else "MISMATCH"
        print(f"{signature:<26} {computed}  {status}")


def print_snapshot(block: int) -> None:
    """Read the USDC reserve at `block` and print the decoded values and utilization."""
    reserve = get_reserve_data(block)
    supplied = get_total_supply_usdc(reserve["a_token"], block)
    borrowed = get_total_supply_usdc(reserve["variable_debt_token"], block)

    print(f"Borrow APR            {reserve['borrow_apr']:.3%}")
    print(f"Supply APR            {reserve['supply_apr']:.3%}")
    print(f"Reserve factor        {reserve['reserve_factor_bps']} bps")
    print(f"aToken                {reserve['a_token']}")
    print(f"Variable debt token   {reserve['variable_debt_token']}")
    print(f"Rate strategy         {reserve['rate_strategy']}")
    print(f"Total supplied        {supplied / 1e9:,.3f}B USDC")
    print(f"Total borrowed        {borrowed / 1e9:,.3f}B USDC")
    print(f"Available liquidity   {(supplied - borrowed) / 1e9:,.3f}B USDC")
    print(f"Utilization           {utilization(borrowed, supplied):.2%}")


def main() -> None:
    check_selectors()

    print(f"\n=== Reference block {REFERENCE_BLOCK:,} ===")
    print(f"Expected: {REFERENCE_VALUES}")
    print_snapshot(REFERENCE_BLOCK)

    latest = get_block_number()
    print(f"\n=== Latest block {latest:,} ===")
    print_snapshot(latest)


if __name__ == "__main__":
    main()
