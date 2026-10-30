import os
import json
import asyncio
import smtplib
import datetime
import httpx
import base64
from email.message import EmailMessage
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Body, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.engine import SearchEngine
from core.countries import COUNTRIES_REGISTRY
from core.schema import SearchResponse, RestockAlert

app = FastAPI(title="StoreStock Core Engine", version="1.1.0")

@app.on_event("startup")
async def startup_event():
    try:
        # Expand default thread pool to 32 workers to prevent WAN scraper starvation
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=32))
    except Exception as e:
        print(f"[Startup] Error setting thread pool executor: {e}")

    try:
        # Launch background restock alert watcher
        from core.alert_watcher import background_alert_watcher
        asyncio.create_task(background_alert_watcher(interval_seconds=600))
    except Exception as e:
        print(f"[Startup] Error starting alert watcher: {e}")

# Enable CORS for external client/API testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".js") or path.endswith(".html") or path.endswith(".css") or path == "/" or path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, post-check=0, pre-check=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

engine = SearchEngine()

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.get("/favicon.ico", include_in_schema=False)
async def favicon_endpoint():
    logo_path = os.path.join(static_dir, "logo.svg")
    return FileResponse(logo_path, media_type="image/svg+xml")

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Sitemap: https://storestock.polychroms.dev/sitemap.xml\n"
    )

@app.get("/sitemap.xml", response_class=Response)
async def sitemap_xml():
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        '    <loc>https://storestock.polychroms.dev/</loc>\n'
        '    <lastmod>2026-10-28</lastmod>\n'
        '    <changefreq>daily</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>'
    )
    return Response(content=xml, media_type="application/xml")

@app.get("/api/countries")
async def get_countries():
    return COUNTRIES_REGISTRY

@app.get("/api/detect-country")
async def detect_country_endpoint(request: Request):
    # Check Cloudflare edge header CF-IPCountry (case-insensitive) or other common proxy headers
    for h in ["cf-ipcountry", "x-country-code", "x-geo-country", "geoip-country"]:
        val = request.headers.get(h)
        if val and val.upper() in COUNTRIES_REGISTRY:
            return {"country": val.upper(), "source": "cloudflare"}
    return {"country": "RO", "source": "default"}

@app.get("/api/architecture/download")
async def download_architecture_endpoint(password: str = Query(..., description="Access password")):
    if password != "radu1234":
        raise HTTPException(status_code=403, detail="Invalid password. Access denied.")
    
    svg_file = os.path.join(static_dir, "storestock_architecture.svg")
    if not os.path.exists(svg_file):
        raise HTTPException(status_code=404, detail="Architecture diagram not found on server.")
        
    return FileResponse(
        path=svg_file,
        filename="storestock_architecture.svg",
        media_type="image/svg+xml"
    )

@app.get("/api/search", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(..., description="Product query to search"),
    country: str = Query("RO", description="ISO 2-letter country code"),
    lat: Optional[float] = Query(None, description="User latitude for distance calculation"),
    lon: Optional[float] = Query(None, description="User longitude for distance calculation")
):
    # Pure cached-only response: Zero server-side scrapes to protect server home IP
    from core.db import get_database_adapter
    adapter = get_database_adapter()
    cached = adapter.get_cached_products(q, country)
    return SearchResponse(
        query=q,
        country_code=country,
        total_results=len(cached),
        in_stock_count=sum(1 for r in cached if r.in_stock),
        execution_time_ms=1.2,
        stores_searched=[],
        results=cached
    )

@app.get("/api/stream")
async def stream_endpoint():
    # Permanently disabled to protect home IP: 100% of search is client-side
    raise HTTPException(status_code=410, detail="Server stream disabled. Search is 100% client-side from browser.")

@app.post("/api/cache/sync")
async def sync_client_cache(payload: dict = Body(...)):
    """
    Client-Side Distributed Cache Seeder:
    Accepts products discovered directly on user client devices/browsers
    and commits them to the TrueNAS persistent DB with branch enrichment.
    """
    query = payload.get("query", "").strip()
    country = payload.get("country", "RO").strip().upper()
    lat = payload.get("lat")
    lon = payload.get("lon")
    items_raw = payload.get("items", [])
    if not query or not items_raw:
        return {"status": "ignored", "saved": 0}

    # Security validation: limit max items per payload
    items_raw = items_raw[:60]

    from core.schema import StoreResult
    from core.db import get_database_adapter
    from core.branches import attach_branch_info

    parsed = []
    enriched_items = []
    for idx, it in enumerate(items_raw):
        try:
            prod_url = it.get("product_url", "")
            # Basic validation: ensure proper HTTP/HTTPS URL
            if not prod_url.startswith("http://") and not prod_url.startswith("https://"):
                continue

            item = StoreResult(**it)
            # Enrich with physical store branch & distance if missing
            if not item.store_branch:
                branch_info = attach_branch_info(item.store_name, idx, lat, lon)
                if branch_info:
                    item.store_branch = branch_info.get("store_branch")
                    item.store_address = branch_info.get("store_address")
                    item.latitude = branch_info.get("latitude")
                    item.longitude = branch_info.get("longitude")
                    item.distance_km = branch_info.get("distance_km")

            parsed.append(item)
            enriched_items.append(item.model_dump())
        except Exception:
            pass

    if parsed:
        adapter = get_database_adapter()
        adapter.save_cached_products(query, country, parsed)
        return {"status": "success", "saved": len(parsed), "items": enriched_items}
    return {"status": "error", "saved": 0}

@app.get("/api/price-history")
async def get_price_history_endpoint(url: str = Query(..., description="Product URL")):
    """Returns historical price data points for a product URL."""
    try:
        from core.db import get_database_adapter
        adapter = get_database_adapter()
        return {"url": url, "history": adapter.get_price_history(url)}
    except Exception as e:
        return {"url": url, "history": [], "error": str(e)}

# --- Restock Alerts Endpoints ---

@app.get("/api/alerts", response_model=list[RestockAlert])
async def list_alerts():
    return engine.alert_manager.get_all_alerts()

@app.post("/api/alerts", response_model=RestockAlert)
async def create_alert(payload: dict = Body(...)):
    query = payload.get("query")
    store_name = payload.get("store_name", "All Stores")
    target_price = payload.get("target_price")
    email = payload.get("email", "user@example.com")
    product_title = payload.get("product_title")
    product_url = payload.get("product_url")

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    return engine.alert_manager.create_alert(
        query=query,
        store_name=store_name,
        target_price=target_price,
        email=email,
        product_title=product_title,
        product_url=product_url
    )

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    success = engine.alert_manager.delete_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "deleted", "id": alert_id}

@app.get("/api/database/stats")
async def database_stats_endpoint():
    """
    Returns real-time diagnostics and metadata about the active storage engine
    (engine type, disk size, total cached objects, in-stock count, unique stores).
    """
    try:
        from core.db import get_database_adapter
        adapter = get_database_adapter()
        return adapter.get_stats()
    except Exception as e:
        return {
            "error": str(e),
            "status": "unhealthy"
        }

# --- Feedback & Bug Report Background Dispatch Task ---

def send_feedback_email_task(feedback_record: dict, screenshot_b64: Optional[str] = None):
    category = feedback_record.get("category", "General Feedback")
    subject = feedback_record.get("subject", "StoreStock User Feedback")
    message = feedback_record.get("message", "")
    email = feedback_record.get("email", "")
    country = feedback_record.get("country", "Not shared")
    city = feedback_record.get("city", "Not shared")
    last_query = feedback_record.get("last_query", "N/A")
    user_agent = feedback_record.get("user_agent", "Unknown")
    timestamp = feedback_record.get("timestamp", "")
    include_location = feedback_record.get("include_location", True)

    location_str = f"{city}, {country}" if include_location and (city or country) else "Not shared by user"

    target_email = os.environ.get("FEEDBACK_TARGET_EMAIL", "feedback@polychroms.dev").strip()
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").replace(" ", "").strip()
    smtp_port = int(str(os.environ.get("SMTP_PORT", 587)).strip())
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "alerts@storestock.app").strip()

    has_screenshot = bool(screenshot_b64)
    screenshot_note = "Attached (see screenshot below)" if has_screenshot else "None attached"

    email_sent = False

    # Strategy A: Deliver via authenticated Gmail SMTP with optional screenshot
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[StoreStock {category}] {subject}"
            msg["From"] = smtp_from
            recipients = [target_email, "rappar2018@gmail.com"]
            msg["To"] = ", ".join(recipients)
            if email and email != "anonymous":
                msg["Reply-To"] = email

            email_body = f"""New StoreStock Feedback Submission:
======================================================
Category:    {category}
Subject:     {subject}
From:        {email or 'Anonymous User'}
Date (UTC):  {timestamp}
Location:    {location_str}
Last Query:  {last_query or 'N/A'}
Screenshot:  {screenshot_note}

User Agent:
{user_agent}

Message / Description:
------------------------------------------------------
{message}
======================================================
"""
            msg.set_content(email_body)

            # Attach screenshot if provided
            if screenshot_b64:
                raw_b64 = screenshot_b64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                try:
                    img_bytes = base64.b64decode(raw_b64)
                    msg.add_attachment(img_bytes, maintype="image", subtype="png", filename="storestock_screenshot.png")
                    print(f"[Feedback] Attached screenshot ({len(img_bytes)} bytes) to email.")
                except Exception as ex:
                    print(f"[Feedback] Could not decode screenshot attachment: {ex}")

            import ssl
            ssl_context = ssl.create_default_context()

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl_context, timeout=12) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                    server.ehlo()
                    server.starttls(context=ssl_context)
                    server.ehlo()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            email_sent = True
            print(f"[Feedback] Background SMTP email sent successfully to {recipients}")
        except Exception as e:
            print(f"[Feedback SMTP ERROR in background task] {type(e).__name__}: {e}")

    # Strategy B: Fallback HTTPS FormSubmit
    if not email_sent:
        try:
            with httpx.Client(timeout=12.0) as client:
                client.post(
                    f"https://formsubmit.co/ajax/{target_email}",
                    json={
                        "name": f"StoreStock Feedback ({category})",
                        "email": email or "anonymous-user@storestock.app",
                        "_subject": f"[StoreStock {category}] {subject}",
                        "Category": category,
                        "Subject": subject,
                        "Sender_Email": email or "Not provided",
                        "Location": location_str,
                        "Last_Query": last_query or "N/A",
                        "Message": message,
                        "Screenshot_Attached": "Yes" if has_screenshot else "No",
                        "User_Agent": user_agent,
                        "_template": "table"
                    },
                    headers={"Content-Type": "application/json", "Accept": "application/json"}
                )
        except Exception as e:
            print(f"[Feedback] Fallback HTTPS email error: {e}")

# --- Fast Feedback API Endpoint ---

@app.post("/api/feedback")
async def submit_feedback(request: Request, background_tasks: BackgroundTasks, payload: dict = Body(...)):
    category = payload.get("category", "General Feedback").strip()
    subject = payload.get("subject", "StoreStock User Feedback").strip()
    message = payload.get("message", "").strip()
    email = payload.get("email", "").strip()
    include_location = bool(payload.get("include_location", True))
    country = payload.get("country", "").strip() if include_location else "Not shared"
    city = payload.get("city", "").strip() if include_location else "Not shared"
    last_query = payload.get("last_query", "").strip()
    screenshot_b64 = payload.get("screenshot")
    user_agent = request.headers.get("user-agent", "Unknown") if request else "Unknown"

    if not message:
        raise HTTPException(status_code=400, detail="Feedback message cannot be empty")

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    feedback_record = {
        "timestamp": timestamp,
        "category": category,
        "subject": subject,
        "message": message,
        "email": email or "anonymous",
        "include_location": include_location,
        "country": country,
        "city": city,
        "last_query": last_query,
        "has_screenshot": bool(screenshot_b64),
        "user_agent": user_agent
    }

    # 1. Immediately log to data/feedback.jsonl (<1ms)
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    feedback_file = os.path.join(data_dir, "feedback.jsonl")
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Feedback] Failed to save feedback locally: {e}")

    # 2. Asynchronously dispatch the email & screenshot in background so the user does NOT wait!
    background_tasks.add_task(send_feedback_email_task, feedback_record, screenshot_b64)

    return {
        "status": "success",
        "saved": True,
        "message": "Feedback submitted! It is being delivered in the background."
    }

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 3000))
    print(f"Starting StoreStock on http://localhost:{port} ...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
