# NFT Wallet Scanner

A fast, rate-limited local CLI tool to score Ethereum NFT collector wallets for whitelist targeting using ONLY the free OpenSea API.

## Setup

1. `python3 -m venv .venv && source .venv/bin/activate` (or `.\.venv\Scripts\activate` on Windows)
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your OpenSea Instant API key.
   - *Note: Free OpenSea API keys expire in 7 days and must be regenerated.*
4. Put target wallets in `input.csv` or `wallets.txt`.

## Usage

Test a small batch:
```bash
python -m src.cli batch input.csv --out data/results.csv --limit 20
```

Run a full batch:
```bash
python -m src.cli batch input.csv --out data/results.csv
```

Rescore existing cache (without spending API calls):
```bash
python -m src.cli rescore
```

## Important Notes
- **API Limits:** Strictly makes exactly 2 calls per wallet (`/collections` and `/events`). Pagination is disabled to maintain this cap.
- **Resuming:** Uses a local SQLite cache (`data/cache.db`). You can hit `Ctrl+C` to pause and rerun the exact same command to resume where you left off.
- **Portfolio Data:** Due to limitations of the OpenSea v2 free tier, ERC-20 token balances are unavailable and marked `UNKNOWN`. Only NFT values are estimated from the `/collections` payload.
