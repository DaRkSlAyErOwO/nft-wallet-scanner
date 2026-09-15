import argparse
import sys
import os
from src.client import OpenSeaClient
from src.cache import CacheDB
from src.scoring import analyze_wallet
from src.batch import run_batch, export_to_csv
from src.colors import CYAN, GREEN, RED, YELLOW, MAGENTA, WHITE, DIM, RESET, get_status_color, get_hand_color, get_score_color

def normalize_out_path(path: str, default: str = "data/results.csv") -> str:
    path = path.strip().replace('"', '').replace("'", "")
    if not path:
        return default
    if os.path.isdir(path):
        return os.path.join(path, "results.csv")
    if not path.endswith('.csv') and not path.endswith('.txt') and not os.path.isfile(path):
        return os.path.join(path, "results.csv")
    return path

def run_interactive_menu():
    while True:
        print(f"\n{CYAN}NFT Wallet Scanner{RESET}")
        print(f"{CYAN}------------------{RESET}")
        print(f"{CYAN}1){RESET} Analyze one wallet")
        print(f"{CYAN}2){RESET} Batch from CSV/TXT")
        print(f"{CYAN}3){RESET} Rescore from cache (no API)")
        print(f"{CYAN}4){RESET} Export / cache status")
        print(f"{CYAN}5){RESET} Clear cache")
        print(f"{CYAN}0){RESET} Exit")
        try:
            choice = input(f"\n{WHITE}Select an option:{RESET} ").strip()
        except KeyboardInterrupt:
            print("\nExiting...")
            break

        if choice == "0":
            break
        elif choice == "1":
            try:
                addr = input(f"{WHITE}Wallet address:{RESET} ").strip()
                if not addr:
                    continue
                port_input = input(f"{WHITE}Include portfolio USD? [y/N]:{RESET} ").strip().lower()
                fetch_port = port_input == 'y'
                
                refresh_input = input(f"{WHITE}Refresh cache? [y/N]:{RESET} ").strip().lower()
                refresh = refresh_input == 'y'
                
                cmd = f'python -m src.cli analyze {addr}'
                if fetch_port: cmd += ' --portfolio'
                if refresh: cmd += ' --refresh'
                
                os.system(cmd)
            except KeyboardInterrupt:
                print()
                continue
        elif choice == "2":
            try:
                def_input = "whitelist_claims_sorted_by_time.csv"
                if not os.path.exists(def_input):
                    def_input = "input.csv"
                    if not os.path.exists(def_input):
                        def_input = "wallets.txt"
                        
                in_path = input(f"{WHITE}Input file path (.csv or .txt) [{def_input}]:{RESET} ").strip().replace('"', '').replace("'", "")
                if not in_path: in_path = def_input
                
                out_path_raw = input(f"{WHITE}Output file path (.csv) [data/results.csv]:{RESET} ")
                out_path = normalize_out_path(out_path_raw)
                print(f"Writing CSV to: {out_path}")
                
                limit_str = input(f"{WHITE}Limit (blank = all wallets):{RESET} ").strip()
                limit = int(limit_str) if limit_str.isdigit() else 0
                
                sleep_str = input(f"{WHITE}Sleep between requests (seconds) [0.55]:{RESET} ").strip()
                try:
                    sleep_val = float(sleep_str) if sleep_str else 0.55
                except ValueError:
                    sleep_val = 0.55
                
                port_input = input(f"{WHITE}Include portfolio values? [y/N]:{RESET} ").strip().lower()
                fetch_port = port_input == 'y'
                
                only_run_input = input(f"{WHITE}Export only wallets from this batch? [y/N]:{RESET} ").strip().lower()
                only_this_run = only_run_input == 'y'
                
                print("Y = skip wallets already in cache. N = refetch those wallets. Cache is shared; a new output filename does not start a blank dataset.")
                resume_input = input(f"{WHITE}Resume previous run? [Y/n]:{RESET} ").strip().lower()
                resume = resume_input != 'n'
                
                cmd = f'python -m src.cli batch "{in_path}" --out "{out_path}"'
                if limit > 0: cmd += f' --limit {limit}'
                if sleep_val != 0.55: cmd += f' --sleep {sleep_val}'
                if fetch_port: cmd += ' --portfolio'
                if not resume: cmd += ' --no-resume'
                if only_this_run: cmd += ' --only-this-run'
                
                print(f"\n{cmd}")
                start = input(f"{WHITE}Start now? [Y/n]:{RESET} ").strip().lower()
                if start == 'n':
                    continue
                
                os.system(cmd)
            except KeyboardInterrupt:
                print()
                continue
        elif choice == "3":
            try:
                out_path_raw = input(f"{WHITE}Output file path [data/results.csv]:{RESET} ")
                out_path = normalize_out_path(out_path_raw)
                
                cmd = f'python -m src.cli rescore --out "{out_path}"'
                os.system(cmd)
            except KeyboardInterrupt:
                print()
                continue
        elif choice == "4":
            try:
                out_path_raw = input(f"{WHITE}Export file path (blank = status only):{RESET} ")
                out_path = normalize_out_path(out_path_raw, default="") if out_path_raw.strip().replace('"', '').replace("'", "") else ""
                cache = CacheDB()
                try:
                    wallets = cache.get_all_wallets()
                    done = sum(1 for w in wallets if w['status'] == 'done')
                    print(f"\nCache Status:")
                    print(f"Total wallets: {len(wallets)}")
                    print(f"Done: {done}")
                    from collections import Counter
                    hands = Counter(w['hand_type'] for w in wallets if w['status'] == 'done')
                    if hands:
                        print("\nHand Types (done):")
                        for h, c in hands.most_common():
                            print(f"  {h}: {c}")
                    
                    if out_path:
                        cmd = f'python -m src.cli export --out "{out_path}"'
                        os.system(cmd)
                finally:
                    cache.close()
            except KeyboardInterrupt:
                print()
                continue
        elif choice == "5":
            print(f"\n{YELLOW}WARNING: Clearing cache means the next batch will refetch every wallet (uses API quota).{RESET}")
            print(f"{YELLOW}This deletes data/cache.db and all saved wallet JSON.{RESET}")
            confirm = input(f"{WHITE}Type DELETE to confirm:{RESET} ").strip()
            if confirm == "DELETE":
                os.system("python -m src.cli clear-cache --yes")
            else:
                print("Cancelled.")
                
def main():
    if len(sys.argv) == 1:
        run_interactive_menu()
        return

    parser = argparse.ArgumentParser(description="NFT Wallet Scanner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Analyze single wallet
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a single wallet address")
    analyze_parser.add_argument("address", help="Ethereum wallet address (0x...)")
    analyze_parser.add_argument("--refresh", action="store_true", help="Force refresh even if cached")
    analyze_parser.add_argument("--portfolio", action="store_true", help="Fetch portfolio value (requires 3rd API call)")

    # Batch process
    batch_parser = subparsers.add_parser("batch", help="Run batch processing")
    batch_parser.add_argument("input_file", help="Input .csv or .txt file with addresses")
    batch_parser.add_argument("--out", required=True, help="Output CSV path")
    batch_parser.add_argument("--limit", type=int, default=0, help="Max wallets to process (for testing)")
    batch_parser.add_argument("--sleep", type=float, default=0.55, help="Seconds to sleep between requests")
    batch_parser.add_argument("--portfolio", action="store_true", help="Fetch portfolio value (requires 3rd API call)")
    batch_parser.add_argument("--no-resume", action="store_true", help="Do not skip already done wallets")
    batch_parser.add_argument("--only-this-run", action="store_true", help="Only export the wallets processed in this batch")

    # Export
    export_parser = subparsers.add_parser("export", help="Export sqlite cache to CSV")
    export_parser.add_argument("--out", required=True, help="Output CSV path")

    # Rescore
    rescore_parser = subparsers.add_parser("rescore", help="Re-run scoring on all cached wallets using their raw JSON data")
    rescore_parser.add_argument("--out", help="Optional output CSV path after rescore")
    
    # Clear cache
    clear_parser = subparsers.add_parser("clear-cache", help="Delete cache database")
    clear_parser.add_argument("--yes", action="store_true", help="Confirm deletion")

    args = parser.parse_args()

    if args.command == "analyze":
        client = OpenSeaClient()
        cache = CacheDB()
        print(f"\nAnalyzing {args.address}...\n")
        try:
            res = analyze_wallet(args.address, client, cache, force_refresh=args.refresh, fetch_portfolio=args.portfolio)
            
            st_color = get_status_color(res.get('status'))
            hand_color = get_hand_color(res.get('hand_type'))
            score_color = get_score_color(res.get('collector_score'))
            
            print(f"\n{CYAN}--- Wallet Report ---{RESET}")
            print(f"Address       : {args.address}")
            print(f"Status        : {st_color}{res.get('status')}{RESET}")
            print(f"NFT Count     : {res.get('nft_count')} (Tier: {res.get('holding_tier')})")
            print(f"Collections   : {res.get('collection_count')}")
            print(f"Verified Colls: {res.get('verified_collections') if res.get('verified_collections') >= 0 else 'Unknown'}")
            print(f"Recent Sales  : {res.get('recent_sales')} (Hand: {hand_color}{res.get('hand_type')}{RESET})")
            print(f"Score         : {score_color}{res.get('collector_score')}{RESET}/100")
            print(f"Confidence    : {res.get('confidence')}%")
            if res.get('portfolio_usd') != "UNKNOWN" or args.portfolio:
                usd = res.get('portfolio_usd')
                pcolor = YELLOW if usd == "UNKNOWN" else GREEN
                print(f"Portfolio USD : {pcolor}{usd}{RESET}")
                print(f"NFT USD       : {res.get('portfolio_nft_usd')}")
                print(f"Token USD     : {res.get('portfolio_token_usd')}")
                print(f"PNL USD       : {res.get('pnl_usd')}")
            
            notes = res.get('notes')
            if notes:
                print(f"Notes         : {YELLOW}{notes}{RESET}")
            if res.get('truncated'):
                print(f"Warning       : {YELLOW}Data was truncated (paginated).{RESET}")
        finally:
            cache.close()
            
    elif args.command == "batch":
        run_batch(args.input_file, args.out, limit=args.limit, sleep_time=args.sleep, fetch_portfolio=args.portfolio, resume=not args.no_resume, only_this_run=args.only_this_run)
        
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
            if args.out:
                export_to_csv(cache, args.out)
        finally:
            cache.close()
            
    elif args.command == "clear-cache":
        if not args.yes:
            print("You must pass --yes to confirm.")
            return
            
        db_path = "data/cache.db"
        for ext in ["", "-wal", "-shm"]:
            p = db_path + ext
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError as e:
                    print(f"Could not remove {p}: {e}")
                    
        # Recreate empty schema
        c = CacheDB(db_path)
        c.close()
        print("Cache cleared.")

if __name__ == "__main__":
    main()
