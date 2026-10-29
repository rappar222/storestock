#!/usr/bin/env python3
"""
StoreStock Internet Scour & Catalog Seeder
Scrapes products across all 50 supported countries and multiple categories,
saving verified store prices, stock, and images directly into the persistent database cache.
"""

import sys
import time
import random
import asyncio
import argparse
from typing import List, Dict, Optional, Tuple
from core.engine import SearchEngine
from core.db import get_database_adapter
from core.countries import COUNTRIES_REGISTRY
from core.schema import StoreResult

# Globally recognizable products that work across all 50 international countries
GLOBAL_QUERIES: Dict[str, List[str]] = {
    "GPUs & Components": [
        "rtx 5090", "rtx 5080", "rtx 5070", "rtx 4090", "rtx 4080 super",
        "rtx 4070 ti super", "rx 7900 xtx", "rtx a6000", "ryzen 7 7800x3d",
        "ryzen 9 9950x", "intel core i9 14900k", "samsung 990 pro 2tb",
        "corsair ddr5 32gb", "seasonic 850w", "asus rog strix b650"
    ],
    "Laptops & Smartphones": [
        "macbook pro m3", "macbook air m2", "iphone 16 pro max", "iphone 15 pro",
        "samsung galaxy s24 ultra", "google pixel 8 pro", "asus rog zephyrus",
        "lenovo legion 5", "dell xps 15", "ipad air m2"
    ],
    "Gaming & Tech": [
        "playstation 5 slim", "xbox series x", "nintendo switch oled",
        "sony wh-1000xm5", "airpods pro 2", "logitech g pro x superlight",
        "hyperx cloud 2", "lg oled 55", "samsung 65 qled tv"
    ],
    "Home & Vehicles": [
        "dyson v15 detect", "roborock s8", "delonghi magnifica",
        "philips airfryer xxl", "tesla model 3", "bmw 3 series", "volkswagen golf"
    ]
}

# Romanian local market items (Fresh groceries, local cars & tech)
RO_LOCAL_QUERIES: Dict[str, List[str]] = {
    "Groceries & Dairy (RO)": [
        "lapte 3.5%", "lapte uht olympus", "lapte napolact 3.5%", "lapte zuzu bio",
        "unt 82%", "unt napolact", "unt albalact 65%",
        "paine feliata toast", "paine integrala secara", "oua proaspete marimea l",
        "cafea boabe lavazza 1kg", "cafea boabe illy", "ulei floarea soarelui 1l",
        "zahar margaritar 1kg", "faina alba 000 baneasa", "apa plata dorna 2l",
        "cascaval rucar", "iaurt grecesc 10% olympus"
    ],
    "Automotive & Local (RO)": [
        "dacia duster", "ulei motor castrol 5w30", "baterie auto varta 74ah",
        "anvelope iarna 205 55 r16", "compresor auto portabil"
    ]
}

def get_country_metadata(code: str) -> Tuple[str, str, str]:
    """Returns (Flag, Country Name, Currency) for a given country code."""
    c_info = COUNTRIES_REGISTRY.get(code.upper(), {})
    flag = c_info.get("flag", "🌐")
    name = c_info.get("name", code.upper())
    currency = c_info.get("currency", "USD")
    return flag, name, currency

async def run_crawler(
    countries: List[str],
    count: int = 25,
    delay_sec: float = 1.5,
    continuous: bool = False,
    sweep_mode: bool = False,
    specific_query: Optional[str] = None
):
    print("=" * 70)
    print("🚀 StoreStock Multi-Country Internet Scourer & Database Populator")
    print(f"🌍 Scope: {len(countries)} Supported Countries")
    print(f"⏱️ Inter-query Delay: {delay_sec}s")
    print("=" * 70)

    engine = SearchEngine()
    db = get_database_adapter()

    # Initial DB Stats
    initial_stats = db.get_stats()
    print("📦 Starting Database State:")
    print(f"   Engine: {initial_stats.get('engine')} ({initial_stats.get('path', 'remote')})")
    print(f"   Cached Products: {initial_stats.get('total_cached_products', 0)}")
    print(f"   Storage Size: {initial_stats.get('file_size_human', '0 B')}")
    print("=" * 70)

    processed_count = 0
    total_saved_this_run = 0
    start_time = time.time()

    # Build work queue
    work_items = []

    if sweep_mode:
        # Sweep mode: takes a single query or top queries and runs through EVERY country sequentially
        sweep_queries = [specific_query] if specific_query else ["rtx 5090", "iphone 16", "macbook pro", "playstation 5"]
        for q in sweep_queries:
            for c_code in countries:
                work_items.append((c_code, "Multi-Country Sweep", q))
    else:
        # Balanced sampling: randomize across countries and categories
        for _ in range(count * 3):
            c_code = random.choice(countries)
            if specific_query:
                work_items.append((c_code, "Manual Query", specific_query.strip()))
            else:
                if c_code == "RO" and random.random() < 0.45:
                    cat = random.choice(list(RO_LOCAL_QUERIES.keys()))
                    q = random.choice(RO_LOCAL_QUERIES[cat])
                else:
                    cat = random.choice(list(GLOBAL_QUERIES.keys()))
                    q = random.choice(GLOBAL_QUERIES[cat])
                work_items.append((c_code, cat, q))

    target_total = len(work_items) if sweep_mode else count

    try:
        while True:
            for c_code, cat, query in work_items:
                if not continuous and processed_count >= target_total:
                    break

                processed_count += 1
                flag, c_name, curr = get_country_metadata(c_code)
                prefix = f"[{processed_count}]" if continuous else f"[{processed_count}/{target_total}]"

                print(f"\n{prefix} {flag} {c_name} ({c_code}) | Scouring '{query}' ({cat})...")

                query_items: List[StoreResult] = []
                store_breakdown: Dict[str, int] = {}
                q_start = time.time()

                try:
                    async for event in engine.stream_search(query, country_code=c_code):
                        if event.get("type") == "provider_result":
                            payload = event.get("payload", {})
                            items_data = payload.get("items", [])
                            store_name = payload.get("store_name", "Store")

                            if items_data:
                                store_breakdown[store_name] = len(items_data)
                                for item_dict in items_data:
                                    try:
                                        query_items.append(StoreResult(**item_dict))
                                    except Exception:
                                        pass
                except Exception as e:
                    print(f"   ⚠️ Search error in {c_code} for '{query}': {e}")

                elapsed = round(time.time() - q_start, 2)

                if query_items:
                    db.save_cached_products(query, c_code, query_items)
                    total_saved_this_run += len(query_items)

                    stores_str = ", ".join([f"{name} ({count})" for name, count in store_breakdown.items()])
                    print(f"   ✅ Saved {len(query_items)} products in {elapsed}s [{curr}]: {stores_str}")
                else:
                    print(f"   ⚪ No products found in {elapsed}s.")

                # Real-time DB stats snapshot
                stats = db.get_stats()
                print(f"   💾 DB Total: {stats.get('total_cached_products')} items ({stats.get('file_size_human')}) across {stats.get('unique_stores')} stores")

                if (continuous or processed_count < target_total) and delay_sec > 0:
                    await asyncio.sleep(delay_sec)

            if not continuous:
                break
            random.shuffle(work_items)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n🛑 Scourer interrupted by user. Finalizing...")

    total_time = round(time.time() - start_time, 1)
    final_stats = db.get_stats()

    print("\n" + "=" * 70)
    print("🏁 Multi-Country Scour Summary:")
    print(f"   Queries Processed: {processed_count}")
    print(f"   Products Saved/Updated This Run: {total_saved_this_run}")
    print(f"   Final Database Records: {final_stats.get('total_cached_products')}")
    print(f"   Final Storage Size: {final_stats.get('file_size_human')}")
    print(f"   Total Time Elapsed: {total_time}s")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(
        description="StoreStock Multi-Country Internet Scourer & Database Populator"
    )
    parser.add_argument(
        "--countries", "-c",
        type=str,
        default="ALL",
        help="Country codes to target: 'ALL' for all 50 countries, or comma-separated e.g. 'RO,US,DE,GB' (default: ALL)"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=25,
        help="Number of queries to scour (default: 25)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=1.5,
        help="Delay in seconds between store queries (default: 1.5)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously in background, cycling across all supported countries"
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Sweep mode: Scour a query systematically across every single one of the 50 countries"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Scour for one specific query across countries"
    )

    args = parser.parse_args()

    # Parse target countries
    all_codes = list(COUNTRIES_REGISTRY.keys())
    if args.countries.strip().upper() == "ALL":
        target_countries = all_codes
    else:
        selected = [code.strip().upper() for code in args.countries.split(",") if code.strip()]
        target_countries = [c for c in selected if c in COUNTRIES_REGISTRY] or ["RO"]

    asyncio.run(run_crawler(
        countries=target_countries,
        count=args.count,
        delay_sec=args.delay,
        continuous=args.continuous,
        sweep_mode=args.sweep,
        specific_query=args.query
    ))

if __name__ == "__main__":
    main()
