"""Project-wide settings: RPC endpoint and contract addresses (Ethereum mainnet)."""

import os

DEFAULT_RPC_URL = "https://eth.drpc.org"

# Aave v3 Pool contract (Ethereum mainnet)
AAVE_V3_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"

# USDC token contract; amounts are integers with 6 decimals (1 USDC = 1_000_000)
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_DECIMALS = 6


def get_rpc_url() -> str:
    """Return the JSON-RPC endpoint, preferring the RPC_URL environment variable."""
    # `or` also covers RPC_URL being set but empty (""), which .get() alone would return as-is.
    return os.environ.get("RPC_URL") or DEFAULT_RPC_URL


if __name__ == "__main__":
    print(get_rpc_url())
