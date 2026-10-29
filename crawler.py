#!/usr/bin/env python3
"""
StoreStock Multi-Core High-Throughput Scourer & Database Populator
Scrapes products across all 50 supported countries and multiple categories
using concurrent worker pools across CPU cores and async I/O.
"""

import os
import sys
import time
import random
import asyncio
import argparse
from concurrent.futures import ThreadPoolExecutor
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
    count: int = 50,
    workers: int = 8,
    delay_sec: float = 0.5,
    continuous: bool = False,
    sweep_mode: bool = False,
    specific_query: Optional[str] = None,
    skip_emag: bool = False
):
    # Configure event loop thread pool executor across CPU cores
    loop = asyncio.get_running_loop()
    cpu_cores = os.cpu_count() or 4
    thread_pool_size = max(workers * 4, cpu_cores * 4, 32)
    loop.set_default_executor(ThreadPoolExecutor(max_workers=thread_pool_size))

    print("=" * 72)
    print("🚀 StoreStock High-Throughput Multi-Core Internet Scourer")
    print(f"⚡ CPU Cores Detected: {cpu_cores} | Active Worker Threads: {workers} (Pool: {thread_pool_size})")
    print(f"🌍 Scope: {len(countries)} Supported Countries")
    print(f"⏱️ Delay per worker: {delay_sec}s")
    if skip_emag:
        print("🛡️ Anti-Bot Shield: eMAG excluded to protect home IP from Cloudflare verification")
    print("=" * 72)

    engine = SearchEngine()
    if skip_emag and "RO" in engine.providers:
        engine.providers["RO"] = [p for p in engine.providers["RO"] if "emag" not in getattr(p, "store_id", "").lower()]

    db = get_database_adapter()

    # Initial DB State
    initial_stats = db.get_stats()
    print("📦 Starting Database State:")
    print(f"   Engine: {initial_stats.get('engine')} ({initial_stats.get('path', 'remote')})")
    print(f"   Cached Products: {initial_stats.get('total_cached_products', 0)}")
    print(f"   Storage Size: {initial_stats.get('file_size_human', '0 B')}")
    print("=" * 72)

    db_write_lock = asyncio.Lock()
    print_lock = asyncio.Lock()

    # Shared Counters
    processed_count = 0
    total_saved_this_run = 0
    start_time = time.time()

    # Queue of work items: (country_code, category, query)
    queue: asyncio.Queue = asyncio.Queue()

    def populate_queue():
        if sweep_mode:
            sweep_queries = [specific_query] if specific_query else ["rtx 5090", "iphone 16", "macbook pro", "playstation 5"]
            for q in sweep_queries:
                for c_code in countries:
                    queue.put_nowait((c_code, "Multi-Country Sweep", q))
        else:
            items_to_generate = max(count * 2, 200)
            for _ in range(items_to_generate):
                c_code = random.choice(countries)
                if specific_query:
                    queue.put_nowait((c_code, "Manual Query", specific_query.strip()))
                else:
                    if c_code == "RO" and random.random() < 0.40:
                        cat = random.choice(list(RO_LOCAL_QUERIES.keys()))
                        q = random.choice(RO_LOCAL_QUERIES[cat])
                    else:
                        cat = random.choice(list(GLOBAL_QUERIES.keys()))
                        q = random.choice(GLOBAL_QUERIES[cat])
                    queue.put_nowait((c_code, cat, q))

    populate_queue()
    target_total = queue.qsize() if sweep_mode else count

    # Worker Task
    async def worker(worker_id: int):
        nonlocal processed_count, total_saved_this_run

        while True:
            # Check exit conditions
            if not continuous and processed_count >= target_total:
                break

            try:
                if queue.empty():
                    if continuous:
                        populate_queue()
                    else:
                        break

                c_code, cat, query = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            query_start = time.time()
            query_items: List[StoreResult] = []
            store_breakdown: Dict[str, int] = {}

            flag, c_name, curr = get_country_metadata(c_code)

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
                async with print_lock:
                    print(f"   [Worker-{worker_id}] ⚠️ Error in {c_code} for '{query}': {e}")

            elapsed = round(time.time() - query_start, 2)

            # Safely serialize DB write across workers
            if query_items:
                async with db_write_lock:
                    db.save_cached_products(query, c_code, query_items)
                    total_saved_this_run += len(query_items)

            processed_count += 1
            cur_speed = round(total_saved_this_run / max(time.time() - start_time, 0.1), 1)

            # Thread-safe log output
            async with print_lock:
                prefix = f"[#{processed_count}]" if continuous else f"[#{processed_count}/{target_total}]"
                stores_str = ", ".join([f"{name} ({c})" for name, c in store_breakdown.items()]) if store_breakdown else "none"
                if query_items:
                    print(
                        f"{prefix} (W-{worker_id}) {flag} {c_code} | '{query}' "
                        f"-> ✅ {len(query_items)} saved ({elapsed}s) [{stores_str}] | ⚡ {cur_speed} items/sec"
                    )
                else:
                    print(f"{prefix} (W-{worker_id}) {flag} {c_code} | '{query}' -> ⚪ 0 found ({elapsed}s)")

                # Snapshot DB stats every 10 queries
                if processed_count % 10 == 0:
                    stats = db.get_stats()
                    print(
                        f"   💾 [DB PROGRESS] Total: {stats.get('total_cached_products')} products "
                        f"({stats.get('file_size_human')}) across {stats.get('unique_stores')} stores\n"
                    )

            queue.task_done()

            if delay_sec > 0:
                await asyncio.sleep(delay_sec)

    # Spawn worker tasks
    actual_worker_count = min(workers, target_total) if not continuous else workers
    worker_tasks = [asyncio.create_task(worker(i + 1)) for i in range(actual_worker_count)]

    try:
        await asyncio.gather(*worker_tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n🛑 Interrupt signal received. Stopping worker pool...")
        for t in worker_tasks:
            t.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)

    total_time = round(time.time() - start_time, 1)
    final_stats = db.get_stats()
    avg_speed = round(total_saved_this_run / max(total_time, 0.1), 1)

    print("\n" + "=" * 72)
    print("🏁 Scour Complete:")
    print(f"   Workers Utilized: {actual_worker_count} concurrent workers")
    print(f"   Queries Completed: {processed_count}")
    print(f"   Products Saved This Run: {total_saved_this_run}")
    print(f"   Throughput Speed: {avg_speed} products / second")
    print(f"   Final Database Records: {final_stats.get('total_cached_products')}")
    print(f"   Final Storage Size: {final_stats.get('file_size_human')}")
    print(f"   Total Time: {total_time}s")
    print("=" * 72)

def main():
    parser = argparse.ArgumentParser(
        description="StoreStock Multi-Core High-Throughput Internet Scourer"
    )
    parser.add_argument(
        "--workers", "-w", "--threads",
        type=int,
        default=8,
        help="Number of concurrent scraper workers / threads (default: 8, recommended: 4-16)"
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
        default=50,
        help="Total number of queries to scour (default: 50)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.5,
        help="Delay in seconds between store queries per worker (default: 0.5s)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Keep running indefinitely across countries with the worker pool"
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Sweep mode: Scour across every single one of the 50 countries in parallel"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Scour for one specific query across countries"
    )
    parser.add_argument(
        "--skip-emag",
        action="store_true",
        help="Skip eMAG during crawling to protect home IP from bot verification"
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
        workers=args.workers,
        delay_sec=args.delay,
        continuous=args.continuous,
        sweep_mode=args.sweep,
        specific_query=args.query,
        skip_emag=args.skip_emag
    ))

if __name__ == "__main__":
    main()
