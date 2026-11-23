# Aave v3 USDC — Interest Rate Curve and Liquidity Risk

**Research question:** How does the interest rate model of the Aave v3 (Ethereum) USDC pool behave in practice,
and how often did depositors face withdrawal-liquidity risk (utilization approaching 100%)?

All on-chain data is read with raw JSON-RPC `eth_call` requests (no web3.py), so every byte of ABI encoding
and decoding is visible in the code.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The RPC endpoint is read from the `RPC_URL` environment variable and defaults to `https://eth.drpc.org`
(a free public node that serves historical `eth_call`). To use another node:

```powershell
$env:RPC_URL = "https://your-node.example"
```

## Project layout

```
src/      Python code
data/     fetched on-chain data (CSV)
charts/   generated figures (PNG)
```

## Status

- [x] M0 — Setup
- [ ] M1 — First on-chain call (`getReserveData`)
- [ ] M2 — Daily historical data
- [ ] M3 — Interest rate strategy parameters over time
- [ ] M4 — Analysis and charts
- [ ] M5 — Findings and limitations
