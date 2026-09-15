import argparse
from src.client import OpenSeaClient
from src.cache import CacheDB
from src.scoring import analyze_wallet
from src.batch import run_batch, export_to_csv

def main():
    parser = argparse.ArgumentParser(description="NFT Wallet Scanner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Analyze single wallet
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a single wallet address")
    analyze_parser.add_argument("address", help="Ethereum wallet address (0x...)")
    analyze_parser.add_argument("--refresh", action="store_true", help="Force refresh even if cached")

    # Batch process
    batch_parser = subparsers.add_parser("batch", help="Run batch processing")
    batch_parser.add_argument("input_file", help="Input .csv or .txt file with addresses")
    batch_parser.add_argument("--out", required=True, help="Output CSV path")
    batch_parser.add_argument("--limit", type=int, default=0, help="Max wallets to process (for testing)")
    batch_parser.add_argument("--sleep", type=int, default=7, help="Seconds to sleep between requests")

    # Export
    export_parser = subparsers.add_parser("export", help="Export sqlite cache to CSV")
    export_parser.add_argument("--out", required=True, help="Output CSV path")

    # Rescore
    subparsers.add_parser("rescore", help="Re-run scoring on all cached wallets using their raw JSON data")

    args = parser.parse_args()

    if args.command == "analyze":
        client = OpenSeaClient()
        cache = CacheDB()
        print(f"Analyzing {args.address}...")
        try:
            res = analyze_wallet(args.address, client, cache, force_refresh=args.refresh)
            
            print("\n--- Wallet Report ---")
            print(f"Address       : {args.address}")
            print(f"Status        : {res.get('status')}")
            print(f"NFT Count     : {res.get('nft_count')} (Tier: {res.get('holding_tier')})")
            print(f"Collections   : {res.get('collection_count')}")
            print(f"Verified Colls: {res.get('verified_collections') if res.get('verified_collections') >= 0 else 'Unknown'}")
            print(f"Recent Sales  : {res.get('recent_sales')} (Hand: {res.get('hand_type')})")
            print(f"Score         : {res.get('collector_score')}/100")
            print(f"Confidence    : {res.get('confidence')}%")
            print(f"Notes         : {res.get('notes')}")
            if res.get('truncated'):
                print("Warning       : Data was truncated (paginated).")
        finally:
            cache.close()
            
    elif args.command == "batch":
        run_batch(args.input_file, args.out, limit=args.limit, sleep_time=args.sleep)
        
    elif args.command == "export":
        cache = CacheDB()
        try:
            export_to_csv(cache, args.out)
        finally:
            cache.close()
            
    elif args.command == "rescore":
        cache = CacheDB()
        try:
            from src.scoring import rescore_wallet
            wallets = cache.get_all_wallets()
            print(f"Rescoring {len(wallets)} wallets...")
            for i, w in enumerate(wallets):
                rescore_wallet(w['address'], cache)
                if i % 100 == 0 and i > 0:
                    print(f"Rescored {i}...")
            print("Rescore complete.")
        finally:
            cache.close()

if __name__ == "__main__":
    main()
