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

## Usage

```powershell
python src/m1_snapshot.py        # USDC reserve snapshot: reference block vs. latest block
python src/m2_fetch_history.py   # daily snapshots -> data/usdc_daily.csv (safe to re-run)
python src/m3_rate_params.py     # rate model parameters per day + periods + model check
python src/m4_analysis.py        # summary numbers + charts/*.png (fetches pool cash on stress days once)
```

## Data notes

- **Sampling:** one snapshot at every block number that is a multiple of 7,200 (≈ one per day).
  A real day has ~7,167 blocks because some 12-second slots stay empty, so the sample time drifts
  a few minutes per day and 4 calendar days are missing between 2024-11-21 and 2026-11-25.
  The fixed grid makes the fetch resumable: re-runs skip blocks that are already saved.
- **Units:** amounts are in USDC and treated as ≈ USD. Rates are annual APRs.
- **Utilization** = variable debt / aToken supply. Stable debt was 0 during the whole window.
  aToken supply excludes the treasury's not-yet-minted share, so on fully drained days this ratio
  reads slightly above 100% (max 100.013%) and supply − debt is slightly negative. On those days
  the pool's actual cash (`getVirtualUnderlyingBalance`) was between ~$0 and ~$60k.

## Project layout

```
src/      Python code
data/     fetched on-chain data (CSV)
charts/   generated figures (PNG)
```

## Status

- [x] M0 — Setup
- [x] M1 — First on-chain call (`getReserveData`)
- [x] M2 — Daily historical data
- [x] M3 — Interest rate strategy parameters over time
- [x] M4 — Analysis and charts
- [ ] M5 — Findings and limitations
