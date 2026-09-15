import json
from typing import Dict, Any, Tuple, Optional
from src.client import OpenSeaClient
from src.cache import CacheDB

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

def calculate_score(nft_count: int, collection_count: int, verified: int, hand_type: str) -> int:
    score = 0
    score += min(35, int((nft_count / 200) * 35)) if nft_count > 0 else 0
    score += min(25, int((collection_count / 20) * 25)) if collection_count > 0 else 0
    if verified >= 0:
        score += min(20, verified * 2)
        
    conviction_scores = {
        "Diamond": 20, "Platinum": 16, "Gold": 12,
        "Paper": 4, "Flipper": 2, "NonCollector": 0, "Empty": 0, "Unknown": 8
    }
    score += conviction_scores.get(hand_type, 8)
    
    return min(100, score)

def parse_and_score(address: str, collections_data: dict, sales_data: dict, col_status: int, sales_status: int, existing_notes: list = None) -> dict:
    notes = existing_notes or []
    
    collections = collections_data.get("collections", [])
    collection_count = len(collections)
    
    nft_count = 0
    has_ownership = False
    verified_collections = -1 
    has_safelist_field = False
    portfolio_nft_usd = 0.0
    has_usd_value = False
    
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
                has_usd_value = True
                portfolio_nft_usd += float(usd_val)

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

    holding_tier = determine_holding_tier(nft_count)
    hand_type = determine_hand_type(nft_count, sells_recent, buys_recent, unknown_side, address, collection_count, len(sales))
    collector_score = calculate_score(nft_count, collection_count, verified_collections, hand_type)
    
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
        
    if has_usd_value:
        notes.append("nft_value_from_collections")
        
    notes.append("portfolio_unavailable")

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
        "portfolio_usd": "UNKNOWN",
        "portfolio_nft_usd": round(portfolio_nft_usd, 2) if has_usd_value else "UNKNOWN",
        "portfolio_token_usd": "UNKNOWN",
        "pnl_usd": "UNKNOWN",
        "verified_collections": verified_collections,
        "truncated": truncated,
        "notes": " | ".join(unique_notes),
        "raw_collections_json": json.dumps(collections_data),
        "raw_sales_json": json.dumps(sales_data)
    }

def analyze_wallet(address: str, client: OpenSeaClient, cache: CacheDB, force_refresh: bool = False) -> Dict[str, Any]:
    address = address.lower()
    
    if not force_refresh:
        cached = cache.get_wallet(address)
        if cached and cached['status'] == 'done':
            return dict(cached)

    notes = []
    
    collections_data = {}
    col_status = 0
    try:
        col_resp = client.get_collections(address)
        col_status = col_resp.status_code
        cache.log_api_call(address, "collections", col_status)
        if col_status == 200:
            collections_data = col_resp.json()
    except Exception as e:
        notes.append(f"Collections fetch error: {str(e)}")

    sales_data = {}
    sales_status = 0
    try:
        sales_resp = client.get_sales(address)
        sales_status = sales_resp.status_code
        cache.log_api_call(address, "sales", sales_status)
        if sales_status == 200:
            sales_data = sales_resp.json()
    except Exception as e:
        notes.append(f"Sales fetch error: {str(e)}")

    result = parse_and_score(address, collections_data, sales_data, col_status, sales_status, notes)
    cache.upsert_wallet(address, result)
    return result

def rescore_wallet(address: str, cache: CacheDB) -> Optional[Dict[str, Any]]:
    address = address.lower()
    w = cache.get_wallet(address)
    if not w:
        return None
        
    try:
        col_data = json.loads(w['raw_collections_json']) if w['raw_collections_json'] else {}
    except:
        col_data = {}
        
    try:
        sales_data = json.loads(w['raw_sales_json']) if w['raw_sales_json'] else {}
    except:
        sales_data = {}
        
    col_status = 200 if col_data else 500
    sales_status = 200 if sales_data else 500
    
    if col_status == 500 and sales_status == 500 and w['status'] != 'done':
        return dict(w) # don't rescore if it was a total api fail
        
    # extract pure notes (not generated by score logic)
    old_notes = w['notes'].split(' | ') if w['notes'] else []
    base_notes = [n for n in old_notes if "fetch error" in n]

    result = parse_and_score(address, col_data, sales_data, col_status, sales_status, base_notes)
    cache.upsert_wallet(address, result)
    return result
