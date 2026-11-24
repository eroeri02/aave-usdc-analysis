"""Aave v3 specific reads and decoding: reserve data, token supplies, utilization."""

from abi import decode_address, decode_uint, encode_address, function_selector, split_words
from config import AAVE_V3_POOL, USDC, USDC_DECIMALS
from rpc import eth_call

RAY = 10**27  # Aave stores rates and indexes as integers scaled by 1e27

# Order of the 15 words returned by Pool.getReserveData(asset)
RESERVE_DATA_FIELDS = [
    "configuration",
    "liquidityIndex",
    "currentLiquidityRate",
    "variableBorrowIndex",
    "currentVariableBorrowRate",
    "currentStableBorrowRate",
    "lastUpdateTimestamp",
    "id",
    "aTokenAddress",
    "stableDebtTokenAddress",
    "variableDebtTokenAddress",
    "interestRateStrategyAddress",
    "accruedToTreasury",
    "unbacked",
    "isolationModeTotalDebt",
]


def get_reserve_words(block: int) -> list[str]:
    """Call getReserveData(USDC) on the Pool and return its 15 raw words."""
    calldata = function_selector("getReserveData(address)") + encode_address(USDC)
    words = split_words(eth_call(AAVE_V3_POOL, calldata, block))
    if len(words) != len(RESERVE_DATA_FIELDS):
        raise ValueError(f"expected {len(RESERVE_DATA_FIELDS)} words, got {len(words)}")
    return words


def decode_reserve_factor(configuration: int) -> int:
    """Reserve factor in basis points, stored in bits 64-79 of the configuration bitmap."""
    # Drop the 64 bits to the right of the field, then keep only its 16 bits.
    return (configuration >> 64) & 0xFFFF


def get_reserve_data(block: int) -> dict:
    """Decode the fields of getReserveData(USDC) that this project uses."""
    words = get_reserve_words(block)
    return {
        "borrow_apr": decode_uint(words[4]) / RAY,
        "supply_apr": decode_uint(words[2]) / RAY,
        "reserve_factor_bps": decode_reserve_factor(decode_uint(words[0])),
        "a_token": decode_address(words[8]),
        "variable_debt_token": decode_address(words[10]),
        "rate_strategy": decode_address(words[11]),
    }


def get_total_supply_usdc(token: str, block: int) -> float:
    """totalSupply() of a USDC-denominated token (aToken or debt token), in whole USDC."""
    words = split_words(eth_call(token, function_selector("totalSupply()"), block))
    return decode_uint(words[0]) / 10**USDC_DECIMALS


def utilization(total_debt: float, total_supply: float) -> float:
    """Share of supplied USDC that is lent out, as a fraction between 0 and 1."""
    if total_supply != 0:
        utilization_ratio = total_debt / total_supply
    else:
        utilization_ratio = 0.0
    return utilization_ratio
