import sqlite3
import os
from datetime import datetime
import json
from typing import Optional, Dict, Any

class CacheDB:
    """
    SQLite caching mechanism for the NFT wallet scanner.
    """
    def __init__(self, db_path="data/cache.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    address TEXT PRIMARY KEY,
                    status TEXT,
                    nft_count INTEGER,
                    collection_count INTEGER,
                    holding_tier TEXT,
                    hand_type TEXT,
                    collector_score INTEGER,
                    confidence INTEGER,
                    recent_sales INTEGER,
                    verified_collections INTEGER,
                    truncated BOOLEAN,
                    notes TEXT,
                    raw_collections_json TEXT,
                    raw_sales_json TEXT,
                    updated_at TIMESTAMP
                )
            """)
            for col, dtype, dflt in [
                ("sells_recent", "INTEGER", "0"),
                ("buys_recent", "INTEGER", "0"),
                ("unknown_side", "INTEGER", "0"),
                ("portfolio_usd", "TEXT", "'UNKNOWN'"),
                ("portfolio_nft_usd", "TEXT", "'UNKNOWN'"),
                ("portfolio_token_usd", "TEXT", "'UNKNOWN'"),
                ("pnl_usd", "TEXT", "'UNKNOWN'"),
                ("raw_portfolio_json", "TEXT", "NULL")
            ]:
                try:
                    self.conn.execute(f"ALTER TABLE wallets ADD COLUMN {col} {dtype} DEFAULT {dflt}")
                except sqlite3.OperationalError:
                    pass
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS api_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT,
                    endpoint TEXT,
                    status_code INTEGER,
                    created_at TIMESTAMP
                )
            """)

    def get_wallet(self, address: str) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM wallets WHERE address = ?", (address.lower(),))
        return cur.fetchone()

    def upsert_wallet(self, address: str, data: Dict[str, Any]):
        with self.conn:
            self.conn.execute("""
                INSERT INTO wallets (
                    address, status, nft_count, collection_count, holding_tier,
                    hand_type, collector_score, confidence, recent_sales,
                    verified_collections, truncated, notes, raw_collections_json,
                    raw_sales_json, raw_portfolio_json, updated_at, sells_recent, buys_recent, unknown_side,
                    portfolio_usd, portfolio_nft_usd, portfolio_token_usd, pnl_usd
                ) VALUES (
                    :address, :status, :nft_count, :collection_count, :holding_tier,
                    :hand_type, :collector_score, :confidence, :recent_sales,
                    :verified_collections, :truncated, :notes, :raw_collections_json,
                    :raw_sales_json, :raw_portfolio_json, :updated_at, :sells_recent, :buys_recent, :unknown_side,
                    :portfolio_usd, :portfolio_nft_usd, :portfolio_token_usd, :pnl_usd
                )
                ON CONFLICT(address) DO UPDATE SET
                    status=excluded.status,
                    nft_count=excluded.nft_count,
                    collection_count=excluded.collection_count,
                    holding_tier=excluded.holding_tier,
                    hand_type=excluded.hand_type,
                    collector_score=excluded.collector_score,
                    confidence=excluded.confidence,
                    recent_sales=excluded.recent_sales,
                    verified_collections=excluded.verified_collections,
                    truncated=excluded.truncated,
                    notes=excluded.notes,
                    raw_collections_json=excluded.raw_collections_json,
                    raw_sales_json=excluded.raw_sales_json,
                    raw_portfolio_json=excluded.raw_portfolio_json,
                    updated_at=excluded.updated_at,
                    sells_recent=excluded.sells_recent,
                    buys_recent=excluded.buys_recent,
                    unknown_side=excluded.unknown_side,
                    portfolio_usd=excluded.portfolio_usd,
                    portfolio_nft_usd=excluded.portfolio_nft_usd,
                    portfolio_token_usd=excluded.portfolio_token_usd,
                    pnl_usd=excluded.pnl_usd
            """, {
                "sells_recent": data.get("sells_recent", 0),
                "buys_recent": data.get("buys_recent", 0),
                "unknown_side": data.get("unknown_side", 0),
                "portfolio_usd": data.get("portfolio_usd", "UNKNOWN"),
                "portfolio_nft_usd": data.get("portfolio_nft_usd", "UNKNOWN"),
                "portfolio_token_usd": data.get("portfolio_token_usd", "UNKNOWN"),
                "pnl_usd": data.get("pnl_usd", "UNKNOWN"),
                "raw_portfolio_json": data.get("raw_portfolio_json", None),
                **data, 
                "address": address.lower(), 
                "updated_at": datetime.utcnow().isoformat()
            })

    def log_api_call(self, address: str, endpoint: str, status_code: int):
        with self.conn:
            self.conn.execute("""
                INSERT INTO api_log (address, endpoint, status_code, created_at)
                VALUES (?, ?, ?, ?)
            """, (address.lower(), endpoint, status_code, datetime.utcnow().isoformat()))

    def get_all_wallets(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM wallets ORDER BY collector_score DESC")
        return cur.fetchall()

    def close(self):
        self.conn.close()
