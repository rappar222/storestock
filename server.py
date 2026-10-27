import os
import json
import asyncio
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
    # Check Cloudflare edge header CF-IPCountry
    cf_country = request.headers.get("cf-ipcountry")
    if cf_country and cf_country.upper() in COUNTRIES_REGISTRY:
        return {"country": cf_country.upper(), "source": "cloudflare"}
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

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 3000))
    print(f"Starting StoreStock on http://localhost:{port} ...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
