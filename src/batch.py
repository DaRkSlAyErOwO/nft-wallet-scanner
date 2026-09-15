import csv
import time
import os
import sys
from collections import Counter
from typing import List
from src.client import OpenSeaClient
from src.cache import CacheDB
from src.scoring import analyze_wallet
from src.colors import GREEN, CYAN, RESET

def extract_addresses(filepath: str) -> List[str]:
    addresses = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        if filepath.endswith('.csv'):
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                return []
            
            wallet_idx = -1
            for i, h in enumerate(headers):
                if 'wallet' in h.strip().lower() or 'address' in h.strip().lower():
                    wallet_idx = i
                    break
                    
            for row in reader:
                if not row: continue
                
                # Auto-detect column from first row if header matching failed
                if wallet_idx == -1:
                    for i, cell in enumerate(row):
                        if cell.strip().startswith('0x') and len(cell.strip()) == 42:
                            wallet_idx = i
                            break
                    if wallet_idx == -1:
                        wallet_idx = 0 # fallback to 0
                        
                if len(row) > wallet_idx:
                    addr = row[wallet_idx].strip()
                    if addr.startswith('0x') and len(addr) == 42:
                        addresses.add(addr.lower())
                    elif addr:
                        pass # Silently skip non-addresses to reduce log spam
        else:
            for line in f:
                addr = line.strip()
                if addr.startswith('0x') and len(addr) == 42:
                    addresses.add(addr.lower())
                elif addr:
                    print(f"Skipping invalid address format: {addr}")
                    
    return list(addresses)

def format_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m"
    else:
        return f"{seconds/3600:.1f}h"

def export_to_csv(cache: CacheDB, out_path: str, quiet: bool = False, addresses_subset: List[str] = None):
    wallets = cache.get_all_wallets()
    if not wallets:
        if not quiet:
            print("No wallets in cache to export.")
        return
        
    if addresses_subset is not None:
        subset_set = set(addresses_subset)
        wallets = [w for w in wallets if w['address'] in subset_set]
        if not wallets:
            if not quiet:
                print("No wallets from this run found in cache to export.")
            return

    if os.path.isdir(out_path):
        out_path = os.path.join(out_path, 'results.csv')
    elif not out_path.endswith('.csv') and not out_path.endswith('.txt') and not os.path.isfile(out_path):
        out_path = os.path.join(out_path, 'results.csv')
        
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        keys = [
            "address", "status", "nft_count", "collection_count", "holding_tier",
            "hand_type", "sells_recent", "buys_recent", "recent_sales",
            "portfolio_usd", "portfolio_nft_usd", "portfolio_token_usd", "pnl_usd",
            "collector_score", "confidence", "truncated", "notes"
        ]
        writer.writerow(keys)
        for w in wallets:
            w_keys = w.keys()
            row = [w[k] if k in w_keys else "" for k in keys]
            writer.writerow(row)
                
    if not quiet:
        print(f"Exported {len(wallets)} wallets to {out_path}")

def run_batch(input_file: str, out_file: str, limit: int = 0, sleep_time: float = 0.55, fetch_portfolio: bool = False, resume: bool = True, only_this_run: bool = False):
    addresses = extract_addresses(input_file)
    print(f"Loaded {len(addresses)} unique valid addresses from {input_file}")
    
    if limit > 0:
        addresses = addresses[:limit]
        print(f"Limiting to {limit} addresses.")
        
    client = OpenSeaClient(min_delay_sec=sleep_time)
    cache = CacheDB()
    
    total = len(addresses)
    done_count = 0
    failed_count = 0
    skipped_count = 0
    
    start_time = time.time()
    
    try:
        for i, addr in enumerate(addresses):
            cached = cache.get_wallet(addr)
            if resume and cached and cached['status'] == 'done':
                skipped_count += 1
                done_count += 1
            else:
                try:
                    res = analyze_wallet(addr, client, cache, force_refresh=True, fetch_portfolio=fetch_portfolio, quiet=True)
                    if res['status'] == 'done':
                        done_count += 1
                    else:
                        failed_count += 1
                except RuntimeError as e:
                    if "API key invalid or expired" in str(e):
                        print(f"\nFATAL: {str(e)}")
                        break
                    else:
                        print(f"\nRuntimeError: {e}")
                        failed_count += 1
                except Exception as e:
                    print(f"\nError processing {addr}: {e}")
                    failed_count += 1
                    
            # Export incrementally
            export_to_csv(cache, out_file, quiet=True, addresses_subset=addresses if only_this_run else None)
            
            # Print progress
            processed = i + 1
            elapsed = time.time() - start_time
            actual_processed = processed - skipped_count
            if actual_processed > 0:
                time_per_wallet = elapsed / actual_processed
                remaining = total - processed
                eta_seconds = remaining * time_per_wallet
            else:
                eta_seconds = 0
                
            pct = processed / total if total > 0 else 0
            bar_len = 20
            filled_len = int(bar_len * pct)
            bar = f"{GREEN}{'#' * filled_len}{RESET}{'-' * (bar_len - filled_len)}"
            pct_str = f"{pct * 100:.1f}%"
            short_addr = f"{addr[:6]}...{addr[-4:]}"
            
            line = f"[{bar}] {processed}/{total}  {GREEN}{pct_str}{RESET}  done={done_count} fail={failed_count} skip={skipped_count}  eta={CYAN}{format_eta(eta_seconds)}{RESET}  {short_addr}"
            sys.stdout.write("\r" + line.ljust(90))
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        print("\n\nBatch interrupted by user. Resume later with the same command.")
        
    finally:
        print("\n\n--- Batch Summary ---")
        print(f"This run: {done_count} processed / {failed_count} failed / {skipped_count} skipped")
        
        wallets = cache.get_all_wallets()
        done_all = sum(1 for w in wallets if w['status'] == 'done')
        failed_all = len(wallets) - done_all
        print(f"\nAll cache: {done_all} processed / {failed_all} failed")
        
        tier_counts = Counter()
        hand_counts = Counter()
        scores = []
        
        for w in wallets:
            if w['status'] == 'done':
                tier_counts[w['holding_tier']] += 1
                hand_counts[w['hand_type']] += 1
                scores.append((w['address'], w['collector_score'], w['holding_tier'], w['hand_type']))
                
        print("\nTop 10 Scores (All Cache):")
        scores.sort(key=lambda x: x[1], reverse=True)
        for i, (addr, score, t, h) in enumerate(scores[:10]):
            print(f"  {i+1}. {addr}: {score} ({t} / {h})")
            
        cache.close()
