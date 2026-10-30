import os
import io
import re
import csv
import gzip
import zipfile
import json
import xml.etree.ElementTree as ET
from typing import Generator, Dict, Any, Optional, List
from core.schema import StoreResult, StockLevel, ProductCategory
from core.catalogs.models import FeedConfig, FeedFormat

def _clean_price(price_val: Any) -> float:
    if price_val is None:
        return 0.0
    if isinstance(price_val, (int, float)):
        return float(price_val)
    s = str(price_val).strip()
    # Remove currency words
    s = re.sub(r'(?i)\b(ron|lei|eur|usd|gbp|chf)\b', '', s)
    s = s.replace(' ', '').replace('\xa0', '').strip()
    if not s:
        return 0.0
    # Handle European format: 1.234,56 -> 1234.56 or 12,50 -> 12.50
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    # Extract leading float
    match = re.search(r'[-+]?\d*\.?\d+', s)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0
    return 0.0

def _clean_bool_stock(val: Any) -> bool:
    if val is None:
        return True
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "in stock", "in_stock", "instock", "in stoc", "stoc suficient", "disponibil", "pe stoc"):
        return True
    if s in ("0", "false", "no", "out of stock", "out_of_stock", "outofstock", "stoc epuizat", "nedisponibil", "fara stoc"):
        return False
    return True

def _get_val(row: Dict[str, Any], candidates: List[str], default: str = "") -> str:
    # First exact match
    for c in candidates:
        if c in row and row[c] is not None:
            v = str(row[c]).strip()
            if v:
                return v
    # Case-insensitive match
    lower_keys = {k.lower(): k for k in row.keys()}
    for c in candidates:
        ck = c.lower()
        if ck in lower_keys:
            orig = lower_keys[ck]
            if row[orig] is not None:
                v = str(row[orig]).strip()
                if v:
                    return v
    return default

def row_to_store_result(row: Dict[str, Any], config: FeedConfig, idx: int) -> Optional[StoreResult]:
    # Determine title
    title_keys = ["title", "name", "product_name", "titlu", "denumire", "nume_produs", "g:title"]
    title = _get_val(row, title_keys)
    if not title:
        return None

    # Determine URL
    url_keys = ["url", "link", "product_url", "aff_code", "affiliate_link", "g:link", "deeplink"]
    url = _get_val(row, url_keys)
    if not url:
        # Fallback dummy URL using ID
        pid = _get_val(row, ["id", "product_id", "item_id", "sku", "g:id"], f"p_{idx}")
        url = f"https://storestock.local/{config.store_name.lower()}/{pid}"

    # Determine Price
    price_keys = ["price", "pret", "final_price", "sale_price", "pret_redus", "g:price", "g:sale_price"]
    price_raw = _get_val(row, price_keys, "0.0")
    price = _clean_price(price_raw)

    # Determine Image
    img_keys = ["image_url", "image", "picture", "picture_url", "img_url", "photo", "g:image_link", "image_link"]
    image_url = _get_val(row, img_keys)
    if not image_url:
        image_url = None

    # Determine Stock
    stock_keys = ["availability", "in_stock", "stock", "stoc", "disponibilitate", "g:availability"]
    stock_raw = _get_val(row, stock_keys, "in stock")
    in_stock = _clean_bool_stock(stock_raw)

    # Determine Brand
    brand_keys = ["brand", "producator", "manufacturer", "g:brand"]
    brand = _get_val(row, brand_keys) or None

    # Determine Category
    cat_keys = ["category", "categorie", "sub_category", "g:product_type"]
    category_str = _get_val(row, cat_keys)
    cat_enum = config.category
    if category_str:
        c_low = category_str.lower()
        if any(w in c_low for w in ["aliment", "dulciuri", "biscuiti", "lapte", "panificatie", "grocery", "groceries"]):
            cat_enum = ProductCategory.GROCERIES
        elif any(w in c_low for w in ["laptop", "pc", "telefon", "tv", "electro", "componente", "gpu"]):
            cat_enum = ProductCategory.TECH_HARDWARE
        elif any(w in c_low for w in ["auto", "anvelope", "piese", "ulei motor"]):
            cat_enum = ProductCategory.AUTOMOTIVE

    pid = _get_val(row, ["id", "product_id", "item_id", "sku", "g:id"], f"feed_{config.id}_{idx}")

    return StoreResult(
        id=f"{config.id}_{pid}",
        store_name=config.store_name,
        store_icon=config.store_icon,
        country_code=config.country_code,
        title=title,
        price=price,
        currency=config.currency,
        in_stock=in_stock,
        stock_level=StockLevel.IN_STOCK if in_stock else StockLevel.OUT_OF_STOCK,
        stock_badge_text="In Stock" if in_stock else "Out of Stock",
        product_url=url,
        image_url=image_url,
        category=cat_enum,
        brand=brand,
        delivery_info=f"Available at {config.store_name}"
    )

def open_feed_stream(file_path: str):
    """Opens a feed file, handling .gz and .zip compression automatically."""
    if file_path.endswith('.gz'):
        return gzip.open(file_path, 'rt', encoding='utf-8', errors='replace')
    elif file_path.endswith('.zip'):
        zf = zipfile.ZipFile(file_path, 'r')
        names = zf.namelist()
        if not names:
            raise ValueError(f"Zip file {file_path} is empty")
        first_file = names[0]
        return io.TextIOWrapper(zf.open(first_file, 'r'), encoding='utf-8', errors='replace')
    else:
        return open(file_path, 'r', encoding='utf-8', errors='replace')

def parse_csv_feed(file_path: str, config: FeedConfig) -> Generator[StoreResult, None, None]:
    """Streams products from a CSV/TSV feed."""
    with open_feed_stream(file_path) as f:
        # Read a sample to detect delimiter if not provided
        sample = f.read(4096)
        f.seek(0)
        delimiter = config.delimiter
        if not delimiter:
            if '\t' in sample:
                delimiter = '\t'
            elif ';' in sample and sample.count(';') > sample.count(','):
                delimiter = ';'
            else:
                delimiter = ','

        reader = csv.DictReader(f, delimiter=delimiter)
        for idx, row in enumerate(reader):
            res = row_to_store_result(row, config, idx)
            if res:
                yield res

def parse_xml_feed(file_path: str, config: FeedConfig) -> Generator[StoreResult, None, None]:
    """Streams products from an XML feed (Google Merchant, RSS, 2Performant) using iterparse."""
    with open_feed_stream(file_path) as f:
        # iterparse takes a binary stream or file-like object
        # Since open_feed_stream returned a text wrapper, if needed reopen or read raw
        pass

    # Read binary stream for iterparse
    if file_path.endswith('.gz'):
        raw_stream = gzip.open(file_path, 'rb')
    elif file_path.endswith('.zip'):
        zf = zipfile.ZipFile(file_path, 'r')
        raw_stream = zf.open(zf.namelist()[0], 'r')
    else:
        raw_stream = open(file_path, 'rb')

    try:
        context = ET.iterparse(raw_stream, events=("end",))
        idx = 0
        for event, elem in context:
            tag_name = elem.tag.split('}')[-1].lower()
            if tag_name in ('item', 'product', 'entry'):
                row = {}
                for child in elem:
                    child_tag = child.tag.split('}')[-1]
                    row[child_tag] = (child.text or "").strip()
                elem.clear()

                res = row_to_store_result(row, config, idx)
                if res:
                    idx += 1
                    yield res
    finally:
        raw_stream.close()

def parse_json_feed(file_path: str, config: FeedConfig) -> Generator[StoreResult, None, None]:
    """Parses JSON array or JSONL feed."""
    with open_feed_stream(file_path) as f:
        first_char = f.read(1)
        f.seek(0)
        if first_char == '[':
            data = json.load(f)
            if isinstance(data, list):
                for idx, row in enumerate(data):
                    if isinstance(row, dict):
                        res = row_to_store_result(row, config, idx)
                        if res:
                            yield res
        else:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        res = row_to_store_result(row, config, idx)
                        if res:
                            yield res
                except Exception:
                    continue

def stream_feed_products(file_path: str, config: FeedConfig) -> Generator[StoreResult, None, None]:
    """Main feed router: dispatches to appropriate parser based on format and file extension."""
    fmt = config.feed_format
    fname = file_path.lower()
    if fmt == FeedFormat.CSV or fname.endswith('.csv') or fname.endswith('.tsv') or '.csv.' in fname:
        yield from parse_csv_feed(file_path, config)
    elif fmt == FeedFormat.XML or fmt == FeedFormat.GOOGLE_MERCHANT or fname.endswith('.xml') or '.xml.' in fname:
        yield from parse_xml_feed(file_path, config)
    elif fmt == FeedFormat.JSON or fname.endswith('.json') or fname.endswith('.jsonl'):
        yield from parse_json_feed(file_path, config)
    else:
        # Default try CSV then XML
        try:
            yield from parse_csv_feed(file_path, config)
        except Exception:
            yield from parse_xml_feed(file_path, config)
