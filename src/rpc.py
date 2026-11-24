"""Minimal JSON-RPC client for an Ethereum node (no web3.py)."""

import requests

from config import get_rpc_url


def rpc_call(method: str, params: list):
    """Send one JSON-RPC request and return its `result` field."""
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    response = requests.post(get_rpc_url(), json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"RPC error for {method}: {body['error']}")
    return body["result"]


def get_block_number() -> int:
    """Return the latest block number."""
    return int(rpc_call("eth_blockNumber", []), 16)


def eth_call(to: str, data: str, block: int) -> str:
    """Run a read-only contract call as of `block`; return the raw hex result."""
    return rpc_call("eth_call", [{"to": to, "data": data}, hex(block)])
