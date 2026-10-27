import os
import json
import asyncio
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.engine import SearchEngine
from core.countries import COUNTRIES_REGISTRY
from core.schema import SearchResponse

app = FastAPI(title="StoreStock Core Engine", version="1.0.0")

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

@app.get("/api/search", response_model=SearchResponse)
async def search_endpoint(
    q: str = Query(..., description="Product query to search"),
    country: str = Query("RO", description="ISO 2-letter country code")
):
    return await engine.search_all(q, country_code=country)

@app.get("/api/stream")
async def stream_endpoint(
    q: str = Query(..., description="Product query to search"),
    country: str = Query("RO", description="ISO 2-letter country code")
):
    """
    Server-Sent Events (SSE) streaming endpoint:
    Streams results from each store as soon as that store's response completes.
    """
    async def event_generator():
        async for provider_res in engine.stream_search(q, country_code=country):
            payload = {
                "type": "provider_result",
                "payload": provider_res
            }
            yield f"data: {json.dumps(payload)}\n\n"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)
