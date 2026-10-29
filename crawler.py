#!/usr/bin/env python3
"""
StoreStock Internet Scour & Catalog Seeder
Scrapes random trending products across tech, groceries, essentials, and vehicles,
saving them directly into the persistent database cache.
"""

import sys
import time
import random
import asyncio
import argparse
from typing import List, Dict
from core.engine import SearchEngine
from core.db import get_database_adapter
from core.schema import StoreResult

# Curated catalog of high-demand search queries across multiple categories
SEED_CATALOG: Dict[str, List[str]] = {
    "GPUs & Components": [
        "rtx 5090", "rtx 5080", "rtx 5070", "rtx 4090", "rtx 4080 super",
        "rtx 4070 ti super", "rtx 4060 ti", "rx 7900 xtx", "rx 7800 xt", "rtx a6000",
        "ryzen 7 7800x3d", "ryzen 9 9950x", "intel core i9 14900k", "core i7 14700k",
        "ssd samsung 990 pro 2tb", "ssd kingston kc3000", "ram ddr5 32gb corsair",
        "sursa seasonic 850w", "placa de baza b650 asus", "cooler noctua nh-d15"
    ],
    "Laptops & Tech": [
        "macbook pro m3", "macbook air m2", "asus rog zephyrus", "lenovo legion 5",
        "dell xps 15", "ipad air", "iphone 16 pro max", "iphone 15",
        "samsung galaxy s24 ultra", "google pixel 8 pro", "tableta xiaomi pad"
    ],
    "Gaming & Displays": [
        "consola ps5 slim", "xbox series x", "nintendo switch oled",
        "monitor oled 144hz", "monitor gaming 27 144hz", "tastatura mecanica wireless",
        "mouse logitech g pro x superlight", "casti hyperx cloud 2 wireless",
        "volan logitech g29", "scaun gaming secretlab"
    ],
    "Groceries & Dairy": [
        "lapte 3.5%", "lapte uht olympus", "lapte napolact 3.5%", "lapte zuzu bio",
        "unt 82%", "unt napolact", "unt albalact 65%",
        "paine feliata toast", "paine integrala secara", "oua proaspete marimea l",
        "cafea boabe lavazza 1kg", "cafea boabe illy", "cafea capsule nespresso",
        "ulei floarea soarelui 1l", "zahar margaritar 1kg", "faina alba 000 baneasa",
        "apa plata dorna 2l", "cascaval rucar", "iaurt grecesc 10% olympus"
    ],
    "Appliances & Home": [
        "aspirator robot roborock", "televizor oled lg 55", "televizor samsung qled",
        "espressor delonghi magnifica", "air fryer philips xxl", "masina de spalat rufe bosch",
        "cuptor cu microunde", "frigider no frost beko", "purificator aer xiaomi"
    ],
    "Automotive & Essentials": [
        "ulei motor castrol 5w30", "ulei motor motul 5w40", "baterie auto varta 74ah",
        "anvelope iarna 205 55 r16", "anvelope all season michelin", "compresor auto portabil",
        "lichid parbriz iarna", "dacia duster", "bmw seria 3", "volkswagen golf 7"
    ]
}

def get_flattened_catalog() -> List[tuple[str, str]]:
    """Returns a list of (category, query) tuples."""
    items = []
    for cat, queries in SEED_CATALOG.items():
        for q in queries:
            items.append((cat, q))
    return items

async def run_crawler(
    count: int = 15,
    country: str = "RO",
    delay_sec: float = 2.0,
    continuous: bool = False,
    specific_query: str = None
):
    print("=" * 65)
    print("🚀 StoreStock Automated Internet Scourer & Database Populator")
    print(f"🌍 Target Country: {country.upper()}")
    print(f"⏱️ Inter-query Delay: {delay_sec}s")
    print("=" * 65)

    engine = SearchEngine()
    db = get_database_adapter()

    # Initial DB Stats
    initial_stats = db.get_stats()
    print(f"📦 Starting Database State:")
    print(f"   Engine: {initial_stats.get('engine')} ({initial_stats.get('path', 'remote')})")
    print(f"   Cached Products: {initial_stats.get('total_cached_products', 0)}")
    print(f"   Storage Size: {initial_stats.get('file_size_human', '0 B')}")
    print("=" * 65)

    catalog = get_flattened_catalog()
    random.shuffle(catalog)

    queries_pool = []
    if specific_query:
        queries_pool = [("Manual Query", specific_query.strip())]
    else:
        queries_pool = catalog

    processed_count = 0
    total_saved_this_run = 0
    start_time = time.time()

    try:
        while True:
            for cat, query in queries_pool:
                if not continuous and processed_count >= count:
                    break

                processed_count += 1
                prefix = f"[{processed_count}]" if continuous else f"[{processed_count}/{count}]"
                print(f"\n{prefix} 🌐 Scouring stores for: '{query}' ({cat})...")

                query_items: List[StoreResult] = []
                store_breakdown: Dict[str, int] = {}
                q_start = time.time()

                try:
                    # Stream search across all relevant providers
                    async for event in engine.stream_search(query, country_code=country):
                        if event.get("type") == "provider_result":
                            payload = event.get("payload", {})
                            items_data = payload.get("items", [])
                            store_name = payload.get("store_name", "Unknown Store")

                            if items_data:
                                store_breakdown[store_name] = len(items_data)
                                for item_dict in items_data:
                                    try:
                                        query_items.append(StoreResult(**item_dict))
                                    except Exception:
                                        pass
                except Exception as e:
                    print(f"   ⚠️ Search error on '{query}': {e}")

                elapsed = round(time.time() - q_start, 2)

                # Persist items to database
                if query_items:
                    db.save_cached_products(query, country, query_items)
                    total_saved_this_run += len(query_items)

                    stores_str = ", ".join([f"{name} ({c})" for name, c in store_breakdown.items()])
                    print(f"   ✅ Saved {len(query_items)} products in {elapsed}s: {stores_str}")
                else:
                    print(f"   ⚪ No products found in {elapsed}s.")

                # Real-time DB stats snapshot
                stats = db.get_stats()
                print(f"   💾 DB Total: {stats.get('total_cached_products')} items ({stats.get('file_size_human')}) across {stats.get('unique_stores')} stores")

                # Respectful delay between queries
                if (continuous or processed_count < count) and delay_sec > 0:
                    await asyncio.sleep(delay_sec)

            if not continuous:
                break
            # Reshuffle for next continuous pass
            random.shuffle(queries_pool)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n🛑 Crawler interrupted by user. Finalizing...")

    total_time = round(time.time() - start_time, 1)
    final_stats = db.get_stats()

    print("\n" + "=" * 65)
    print("🏁 Scour Summary:")
    print(f"   Queries Processed: {processed_count}")
    print(f"   Products Saved/Updated This Run: {total_saved_this_run}")
    print(f"   Final Database Records: {final_stats.get('total_cached_products')}")
    print(f"   Final Storage Size: {final_stats.get('file_size_human')}")
    print(f"   Total Time Elapsed: {total_time}s")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(
        description="StoreStock Background Internet Scourer & Database Populator"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=15,
        help="Number of random queries to scour (default: 15)"
    )
    parser.add_argument(
        "--country", "-c",
        type=str,
        default="RO",
        help="Target country code (RO, US, DE, GB, etc. default: RO)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=2.0,
        help="Delay in seconds between store queries (default: 2.0)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Keep running in the background indefinitely scouring random products"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Scour for one specific query instead of random selection"
    )

    args = parser.parse_args()

    asyncio.run(run_crawler(
        count=args.count,
        country=args.country,
        delay_sec=args.delay,
        continuous=args.continuous,
        specific_query=args.query
    ))

if __name__ == "__main__":
    main()
