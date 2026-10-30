#!/usr/bin/env python3
"""
StoreStock Affiliate Catalog Sync & Feed Ingestion Engine
Downloads and ingests full retailer product catalogs from affiliate feeds (2Performant, Profitshare, Google Merchant XML/CSV).
Safely runs without risking IP bans from live scraping.
"""

import sys
import argparse
import asyncio
from core.catalogs import get_catalog_manager, FeedConfig, FeedFormat
from core.db import get_database_adapter

def cmd_list(args):
    cm = get_catalog_manager()
    feeds = cm.list_feeds()
    print("=" * 70)
    print(f"📦 Configured Affiliate Feeds ({len(feeds)} total):")
    print("=" * 70)
    for f in feeds:
        status = f.last_status or "Not synced yet"
        enabled_str = "✅ Active" if f.enabled else "⏸️ Disabled"
        print(f"• [{f.id}] {f.name} ({f.store_name} - {f.country_code})")
        print(f"  URL: {f.feed_url}")
        print(f"  Format: {f.feed_format} | Status: {enabled_str} | Items: {f.items_count or 0}")
        print(f"  Last Sync: {status}\n")

def cmd_seed(args):
    cm = get_catalog_manager()
    count = cm.ensure_seeded()
    print(f"✅ Catalog seed completed: {count} items processed.")

def cmd_sync(args):
    cm = get_catalog_manager()
    print("🚀 Starting Affiliate Catalog Ingestion...")
    feed_id = args.feed_id
    if feed_id:
        print(f"⏳ Syncing specific feed '{feed_id}'...")
        res = asyncio.run(cm.sync_feed(feed_id))
        if res.success:
            print(f"✅ Success! Ingested {res.items_saved} items from {res.store_name} in {res.duration_seconds}s")
        else:
            print(f"❌ Failed to ingest feed: {res.error}")
    else:
        print("⏳ Syncing all active affiliate feeds...")
        results = asyncio.run(cm.sync_all_active_feeds())
        total_saved = sum(r.items_saved for r in results if r.success)
        print(f"\n🏁 Finished syncing all feeds. Total products ingested: {total_saved}")
        for r in results:
            icon = "✅" if r.success else "❌"
            print(f" {icon} {r.store_name} ({r.feed_id}): {r.items_saved} items in {r.duration_seconds}s")

def cmd_stats(args):
    db = get_database_adapter()
    stats = db.get_stats()
    print("=" * 60)
    print("📊 StoreStock Catalog Database Stats:")
    print("=" * 60)
    print(f"Total Products Ingested: {stats.get('total_cached_products')}")
    print(f"Unique Stores:           {stats.get('unique_stores')}")
    print(f"Storage File Size:       {stats.get('file_size_human')}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="StoreStock Affiliate Catalog Downloader & Sync CLI")
    subparsers = parser.add_subparsers(dest="command")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync/download affiliate feeds")
    sync_parser.add_argument("--feed-id", "-f", type=str, default=None, help="Optional feed ID to sync individually")

    # list command
    subparsers.add_parser("list", help="List all configured affiliate feeds")

    # seed command
    subparsers.add_parser("seed", help="Ensure default seed catalog items exist in database")

    # stats command
    subparsers.add_parser("stats", help="Show database catalog stats")

    # Fallback support for flags: --sync-feeds, --seed, etc.
    parser.add_argument("--sync-feeds", action="store_true", help="Sync all active feeds")
    parser.add_argument("--feed-id", type=str, default=None, help="Specific feed ID to sync")
    parser.add_argument("--seed", action="store_true", help="Seed default catalog items")
    parser.add_argument("--list-feeds", action="store_true", help="List configured feeds")

    args = parser.parse_args()

    if args.command == "sync" or args.sync_feeds:
        cmd_sync(args)
    elif args.command == "list" or args.list_feeds:
        cmd_list(args)
    elif args.command == "seed" or args.seed:
        cmd_seed(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        # Default action: sync feeds if any enabled, else seed and show stats
        cm = get_catalog_manager()
        cm.ensure_seeded()
        active_feeds = [f for f in cm.list_feeds() if f.enabled]
        if active_feeds:
            cmd_sync(args)
        else:
            print("ℹ️ No external affiliate feeds are enabled yet. Default catalog is seeded and ready.")
            cmd_stats(args)

if __name__ == "__main__":
    main()
