import json
from typing import Dict, Any, Tuple, Optional
from src.client import OpenSeaClient
from src.cache import CacheDB
from src.colors import RED, GREEN, CYAN, YELLOW, RESET

def determine_holding_tier(nft_count: int) -> str:
    if nft_count == 0: return "Empty"
    if 1 <= nft_count <= 9: return "Micro"
    if 10 <= nft_count <= 49: return "Small"
    if 50 <= nft_count <= 99: return "Medium"
    if 100 <= nft_count <= 499: return "Large"
    return "Whale"

def determine_hand_type(nft_count: int, sells: int, buys: int, unknown: int, address: str, collection_count: int, total_events: int) -> str:
    if address == "0x0000000000000000000000000000000000000000" or (nft_count == 0 and collection_count == 0):
        return "NonCollector"
        
    if total_events > 0 and unknown > total_events / 2:
        return "Unknown"
        
    if nft_count == 0 and sells == 0 and buys == 0:
        return "Empty"
        
    if sells == 0 and buys == 0 and nft_count < 5:
        return "Inactive"
        
    if sells >= 20 and nft_count < 10:
        return "Flipper"
    if sells >= nft_count and nft_count > 0:
        return "Paper"
    if nft_count >= 20 and sells <= 3:
        return "Diamond"
    if nft_count >= 10 and sells <= 8:
        return "Platinum"
    if nft_count >= 5:
        return "Gold"
    return "Unknown"

def calculate_score(nft_count: int, collection_count: int, verified: int, hand_type: str, raw_portfolio_usd: float, effective_nft_usd: float) -> int:
    money_points = 0
    
    usd_for_score = -1.0
    if raw_portfolio_usd >= 0:
        usd_for_score = raw_portfolio_usd
    elif effective_nft_usd >= 0:
        usd_for_score = effective_nft_usd

    activity_scores = {
        "Diamond": 30,
        "Platinum": 24,
        "Gold": 18,
        "Paper": 8,
        "Flipper": 6,
        "Inactive": 0,
        "Empty": 0,
        "NonCollector": 0,
        "Unknown": 8
    }
    
    activity_points = activity_scores.get(hand_type, 8)

    if usd_for_score < 25:
        money_points = 0
        activity_points = min(activity_points, 5)
    else:
        money_points = min(70, int((usd_for_score / 1000.0) * 70))
    
    return min(100, money_points + activity_points)

def parse_and_score(address: str, collections_data: dict, sales_data: dict, col_status: int, sales_status: int, portfolio_data: dict = None, port_status: int = 500, existing_notes: list = None) -> dict:
    notes = existing_notes or []
    portfolio_data = portfolio_data or {}
    
    collections = collections_data.get("collections", [])
    collection_count = len(collections)
    
    nft_count = 0
    has_ownership = False
    verified_collections = -1 
    has_safelist_field = False
    collection_usd_sum = 0.0
    has_collection_usd = False
    
    if collections:
        if any('safelist_request_status' in c for c in collections):
            has_safelist_field = True
            verified_collections = sum(1 for c in collections if c.get('safelist_request_status') in ('verified', 'approved'))

        for c in collections:
            owned = c.get('owned_asset_count')
            if owned is not None:
                has_ownership = True
                nft_count += int(owned)

            usd_val = c.get('usd_value')
            if usd_val is not None:
                has_collection_usd = True
                collection_usd_sum += float(usd_val)

    # Override portfolio variables if real portfolio endpoint succeeded
    portfolio_usd_val = "UNKNOWN"
    portfolio_token_usd_val = "UNKNOWN"
    pnl_usd_val = "UNKNOWN"
    portfolio_nft_usd_api = -1.0
    
    if port_status == 200 and portfolio_data:
        try:
            if 'total_value_usd' in portfolio_data:
                portfolio_usd_val = round(float(portfolio_data['total_value_usd']), 2)
            if 'nft_value_usd' in portfolio_data:
                portfolio_nft_usd_api = float(portfolio_data['nft_value_usd'])
            if 'token_value_usd' in portfolio_data:
                portfolio_token_usd_val = round(float(portfolio_data['token_value_usd']), 2)
            if 'pnl_absolute' in portfolio_data:
                pnl_usd_val = round(float(portfolio_data['pnl_absolute']), 2)
            else:
                pnl_usd_val = 0.0
        except (ValueError, TypeError):
            pass

    effective_nft_usd = -1.0
    if portfolio_nft_usd_api >= 0:
        effective_nft_usd = portfolio_nft_usd_api
        notes.append("nft_value_from_portfolio")
    elif has_collection_usd:
        effective_nft_usd = collection_usd_sum
        notes.append("nft_value_from_collections")

    if not collections and col_status != 200:
        nft_count = 0
    elif not has_ownership:
        nft_count = collection_count
        notes.append("nft_count fallback to collection_count")

    if not has_safelist_field and col_status == 200:
        notes.append("verified_unknown")

    sales = sales_data.get("asset_events", [])
    sells_recent = 0
    buys_recent = 0
    unknown_side = 0
    
    for event in sales:
        seller = event.get('seller', '').lower()
        buyer = event.get('buyer', '').lower()
        if seller == address:
            sells_recent += 1
        elif buyer == address:
            buys_recent += 1
        else:
            unknown_side += 1
            
    truncated = False
    if collections_data.get("next") or sales_data.get("next"):
        truncated = True

    if address == "0x0000000000000000000000000000000000000000" or (nft_count == 0 and collection_count == 0):
        notes.append("non_collector_or_burn")

    raw_portfolio_usd = -1.0
    if portfolio_usd_val != "UNKNOWN":
        raw_portfolio_usd = float(portfolio_usd_val)
        
    holding_tier = determine_holding_tier(nft_count)
    hand_type = determine_hand_type(nft_count, sells_recent, buys_recent, unknown_side, address, collection_count, len(sales))
    collector_score = calculate_score(nft_count, collection_count, verified_collections, hand_type, raw_portfolio_usd, effective_nft_usd)
    
    confidence = 0
    if col_status == 200 and sales_status == 200:
        confidence = 90
    elif col_status == 200:
        confidence = 60
    elif sales_status == 200:
        confidence = 40
    else:
        confidence = 10
        
    if truncated:
        confidence -= 15
        
    if sales and unknown_side > len(sales) / 2:
        confidence -= 20
        notes.append("role_parsing_failed")
        
    if port_status != 200:
        notes.append("portfolio_unavailable")
        
    if raw_portfolio_usd < 0 and effective_nft_usd < 0:
        confidence -= 10

    # Filter out dup notes
    unique_notes = list(dict.fromkeys(notes))

    return {
        "status": "done" if confidence > 10 else "error",
        "nft_count": nft_count,
        "collection_count": collection_count,
        "holding_tier": holding_tier,
        "hand_type": hand_type,
        "collector_score": collector_score,
        "confidence": max(0, confidence),
        "recent_sales": sells_recent, # legacy col
        "sells_recent": sells_recent,
        "buys_recent": buys_recent,
        "unknown_side": unknown_side,
        "portfolio_usd": portfolio_usd_val,
        "portfolio_nft_usd": round(effective_nft_usd, 2) if effective_nft_usd >= 0 else "UNKNOWN",
        "portfolio_token_usd": portfolio_token_usd_val,
        "pnl_usd": pnl_usd_val,
        "verified_collections": verified_collections,
        "truncated": truncated,
        "notes": " | ".join(unique_notes),
        "raw_collections_json": json.dumps(collections_data),
        "raw_sales_json": json.dumps(sales_data),
        "raw_portfolio_json": json.dumps(portfolio_data) if portfolio_data else None
    }

def analyze_wallet(address: str, client: OpenSeaClient, cache: CacheDB, force_refresh: bool = False, fetch_portfolio: bool = False, quiet: bool = False) -> Dict[str, Any]:
    address = address.lower()
    
    if not force_refresh:
        cached_row = cache.get_wallet(address)
        if cached_row and cached_row['status'] == 'done':
            cached = dict(cached_row)
            has_portfolio = False
            if cached.get('raw_portfolio_json'):
                try:
                    pj = json.loads(cached['raw_portfolio_json'])
                    if 'total_value_usd' in pj:
                        has_portfolio = True
                except:
                    pass
            if not fetch_portfolio or has_portfolio:
                return dict(cached)

    notes = []
    
    total_steps = 3 if fetch_portfolio else 2
    
    collections_data = {}
    col_status = 0
    try:
        if not quiet: print(f"{CYAN}[1/{total_steps}]{RESET} Fetching collections...", end="", flush=True)
        col_resp = client.get_collections(address)
        col_status = col_resp.status_code
        cache.log_api_call(address, "collections", col_status)
        if col_status == 200:
            collections_data = col_resp.json()
            if not quiet: print(f" {GREEN}OK{RESET}")
        else:
            if not quiet: print(f" {RED}Failed ({col_status}){RESET}")
    except Exception as e:
        if not quiet: print(f" {RED}Error{RESET}")
        notes.append(f"Collections fetch error: {str(e)}")

    sales_data = {}
    sales_status = 0
    try:
        if not quiet: print(f"{CYAN}[2/{total_steps}]{RESET} Fetching sales...", end="", flush=True)
        sales_resp = client.get_sales(address)
        sales_status = sales_resp.status_code
        cache.log_api_call(address, "sales", sales_status)
        if sales_status == 200:
            sales_data = sales_resp.json()
            if not quiet: print(f" {GREEN}OK{RESET}")
        else:
            if not quiet: print(f" {RED}Failed ({sales_status}){RESET}")
    except Exception as e:
        if not quiet: print(f" {RED}Error{RESET}")
        notes.append(f"Sales fetch error: {str(e)}")

    portfolio_data = {}
    port_status = 500
    if fetch_portfolio:
        try:
            if not quiet: print(f"{CYAN}[3/{total_steps}]{RESET} Fetching portfolio...", end="", flush=True)
            port_resp = client.get_portfolio(address)
            port_status = port_resp.status_code
            cache.log_api_call(address, "portfolio", port_status)
            if port_status == 200:
                portfolio_data = port_resp.json()
                if not quiet: print(f" {GREEN}OK{RESET}")
            else:
                if not quiet: print(f" {RED}Failed ({port_status}){RESET}")
        except Exception as e:
            if not quiet: print(f" {RED}Error{RESET}")
            notes.append(f"Portfolio fetch error: {str(e)}")

    result = parse_and_score(address, collections_data, sales_data, col_status, sales_status, portfolio_data, port_status, notes)
    cache.upsert_wallet(address, result)
    return result

def rescore_wallet(address: str, cache: CacheDB) -> Optional[Dict[str, Any]]:
    address = address.lower()
    w_row = cache.get_wallet(address)
    if not w_row:
        return None
    w = dict(w_row)
        
    try:
        col_data = json.loads(w['raw_collections_json']) if w['raw_collections_json'] else {}
    except:
        col_data = {}
        
    try:
        sales_data = json.loads(w['raw_sales_json']) if w['raw_sales_json'] else {}
    except:
        sales_data = {}
        
    try:
        portfolio_data = json.loads(w['raw_portfolio_json']) if w.get('raw_portfolio_json') else {}
    except:
        portfolio_data = {}
        
    col_status = 200 if col_data else 500
    sales_status = 200 if sales_data else 500
    port_status = 200 if portfolio_data else 500
    
    if col_status == 500 and sales_status == 500 and w['status'] != 'done':
        return dict(w) # don't rescore if it was a total api fail
        
    # extract pure notes (not generated by score logic)
    old_notes = w['notes'].split(' | ') if w['notes'] else []
    base_notes = [n for n in old_notes if "fetch error" in n]

    result = parse_and_score(address, col_data, sales_data, col_status, sales_status, portfolio_data, port_status, base_notes)
    cache.upsert_wallet(address, result)
    return result
