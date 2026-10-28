import os
import json
import asyncio
import smtplib
import datetime
from email.message import EmailMessage
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Body, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.engine import SearchEngine
from core.countries import COUNTRIES_REGISTRY
from core.schema import SearchResponse, RestockAlert

app = FastAPI(title="StoreStock Core Engine", version="1.1.0")

# Enable CORS for external client/API testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = SearchEngine()

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

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

@app.get("/api/search", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(..., description="Product query to search"),
    country: str = Query("RO", description="ISO 2-letter country code"),
    lat: Optional[float] = Query(None, description="User latitude for distance calculation"),
    lon: Optional[float] = Query(None, description="User longitude for distance calculation")
):
    return await engine.search_all(q, country_code=country, user_lat=lat, user_lon=lon)

@app.get("/api/stream")
async def stream_endpoint(
    q: str = Query(..., description="Product query to search"),
    country: str = Query("RO", description="ISO 2-letter country code"),
    lat: Optional[float] = Query(None, description="User latitude for distance calculation"),
    lon: Optional[float] = Query(None, description="User longitude for distance calculation")
):
    """
    Server-Sent Events (SSE) streaming endpoint:
    Streams results from each store as soon as that store's response completes.
    """
    async def event_generator():
        async for event in engine.stream_search(q, country_code=country, user_lat=lat, user_lon=lon):
            yield f"data: {json.dumps(event)}\n\n"
        # Done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

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

# --- Feedback & Bug Report Endpoint ---

@app.post("/api/feedback")
async def submit_feedback(request: Request, payload: dict = Body(...)):
    category = payload.get("category", "General Feedback").strip()
    subject = payload.get("subject", "StoreStock User Feedback").strip()
    message = payload.get("message", "").strip()
    email = payload.get("email", "").strip()
    country = payload.get("country", "").strip()
    city = payload.get("city", "").strip()
    last_query = payload.get("last_query", "").strip()
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
        "country": country,
        "city": city,
        "last_query": last_query,
        "user_agent": user_agent
    }

    # 1. Persist to data/feedback.jsonl
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    feedback_file = os.path.join(data_dir, "feedback.jsonl")
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Feedback] Failed to save feedback locally: {e}")

    # 2. Attempt SMTP dispatch to feedback@polychroms.dev
    target_email = "feedback@polychroms.dev"
    smtp_host = os.environ.get("SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "25"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", email or "feedback-noreply@polychroms.dev")

    email_sent = False
    try:
        msg = EmailMessage()
        msg["Subject"] = f"[StoreStock {category}] {subject}"
        msg["From"] = smtp_from
        msg["To"] = target_email
        if email:
            msg["Reply-To"] = email

        email_body = f"""New StoreStock Feedback Submission:
======================================================
Category:   {category}
Subject:    {subject}
From:       {email or 'Anonymous User'}
Date (UTC): {timestamp}
Country:    {country or 'N/A'}
City:       {city or 'N/A'}
Last Query: {last_query or 'N/A'}

User Agent:
{user_agent}

Message / Description:
------------------------------------------------------
{message}
======================================================
"""
        msg.set_content(email_body)

        if smtp_user and smtp_pass:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=5) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                    if os.environ.get("SMTP_TLS", "true").lower() == "true":
                        server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            email_sent = True
        else:
            # Try unauthenticated relay
            with smtplib.SMTP(smtp_host, smtp_port, timeout=3) as server:
                server.send_message(msg)
            email_sent = True
    except Exception as e:
        print(f"[Feedback] Notice: Direct SMTP dispatch failed ({e}). Feedback is safely stored in {feedback_file}")

    return {
        "status": "success",
        "saved": True,
        "email_dispatched": email_sent,
        "target": target_email,
        "message": "Feedback received and stored successfully!"
    }

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 3000))
    print(f"Starting StoreStock on http://localhost:{port} ...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
