import csv
import time
import os
import sys
from collections import Counter
from typing import List
from src.client import OpenSeaClient
from src.cache import CacheDB
from src.scoring import analyze_wallet

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

def export_to_csv(cache: CacheDB, out_path: str, quiet: bool = False):
    wallets = cache.get_all_wallets()
    if not wallets:
        if not quiet:
            print("No wallets in cache to export.")
        return
        
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        keys = wallets[0].keys()
        writer.writerow(keys)
        for w in wallets:
            writer.writerow([w[k] for k in keys])
                
    if not quiet:
        print(f"Exported {len(wallets)} wallets to {out_path}")

def run_batch(input_file: str, out_file: str, limit: int = 0, sleep_time: int = 7):
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
            if cached and cached['status'] == 'done':
                skipped_count += 1
                done_count += 1
            else:
                try:
                    res = analyze_wallet(addr, client, cache, force_refresh=True)
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
            export_to_csv(cache, out_file, quiet=True)
            
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
                
            sys.stdout.write(f"\r{processed} / {total} (done={done_count} failed={failed_count} skipped={skipped_count}) eta={format_eta(eta_seconds)}")
            sys.stdout.flush()
            
    except KeyboardInterrupt:
        print("\n\nBatch interrupted by user. Resume later with the same command.")
        
    finally:
        print("\n\n--- Batch Summary ---")
        wallets = cache.get_all_wallets()
        tier_counts = Counter()
        hand_counts = Counter()
        scores = []
        
        for w in wallets:
            if w['status'] == 'done':
                tier_counts[w['holding_tier']] += 1
                hand_counts[w['hand_type']] += 1
                scores.append((w['address'], w['collector_score'], w['holding_tier'], w['hand_type']))
                
        print("\nHolding Tiers:")
        for t, c in tier_counts.most_common():
            print(f"  {t}: {c}")
            
        print("\nHand Types:")
        for h, c in hand_counts.most_common():
            print(f"  {h}: {c}")
            
        print("\nTop 20 Scores:")
        scores.sort(key=lambda x: x[1], reverse=True)
        for i, (addr, score, t, h) in enumerate(scores[:20]):
            print(f"  {i+1}. {addr}: {score} ({t} / {h})")
            
        cache.close()
