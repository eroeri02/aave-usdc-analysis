"""Minimal JSON-RPC client for an Ethereum node (no web3.py), with throttle and retry."""

import time

import requests

from config import get_rpc_url

MIN_SECONDS_BETWEEN_REQUESTS = 0.1  # throttle: stay polite to the free public node
MAX_ATTEMPTS = 8  # retry transient failures; waits 2+4+...+128 s (~4 min) before giving up

_last_request_time = 0.0


class ContractReverted(Exception):
    """The contract call itself reverted. This is permanent, so it is never retried."""


def _wait_for_throttle() -> None:
    """Sleep just long enough to keep MIN_SECONDS_BETWEEN_REQUESTS between requests."""
    global _last_request_time
    wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.time() - _last_request_time)
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.time()


def _post_once(method: str, params: list):
    """Send a single JSON-RPC request; raise on HTTP or RPC errors."""
    _wait_for_throttle()
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    response = requests.post(get_rpc_url(), json=payload, timeout=30)
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        if "revert" in str(body["error"].get("message", "")).lower():
            raise ContractReverted(f"{method} reverted: {body['error']}")
        raise RuntimeError(f"RPC error for {method}: {body['error']}")
    return body["result"]


def rpc_call(method: str, params: list):
    """Send one JSON-RPC request, retrying with exponential backoff; return `result`."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _post_once(method, params)
        except (requests.RequestException, RuntimeError) as error:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = 2**attempt  # 2, 4, 8, ... seconds
            print(f"  retry {attempt}/{MAX_ATTEMPTS - 1} for {method} in {delay}s: {error}")
            time.sleep(delay)


def get_block_number() -> int:
    """Return the latest block number."""
    return int(rpc_call("eth_blockNumber", []), 16)


def get_block_timestamp(block: int) -> int:
    """Unix timestamp (seconds, UTC) of a block, read from its header."""
    header = rpc_call("eth_getBlockByNumber", [hex(block), False])
    return int(header["timestamp"], 16)


def eth_call(to: str, data: str, block: int) -> str:
    """Run a read-only contract call as of `block`; return the raw hex result."""
    return rpc_call("eth_call", [{"to": to, "data": data}, hex(block)])
