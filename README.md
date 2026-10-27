# 🏪 StoreStock — Real-Time Multi-Store Inventory Engine

**StoreStock** is a unified real-time inventory and stock search engine. Type any product—from enterprise workstations & GPUs (like **NVIDIA A6000 / RTX**) to daily **groceries & hypermarket goods** (milk, coffee, essentials)—and StoreStock checks store availability in parallel.

## 🚀 Live Demo & Testing
The engine is currently running on **Port 3000**:
* **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
* **REST Search API**: `GET /api/search?q={query}&country={country_code}`
* **Server-Sent Events (SSE) Live Stream**: `GET /api/stream?q={query}&country={country_code}`
* **Countries Registry**: `GET /api/countries`

---

## ⚡ Active Providers in Core Engine
1. **eMAG (RO)**: Romania's #1 marketplace (everything from electronics to groceries).
2. **Altex (RO)**: High-speed native JSON search engine via Fenrir API.
3. **Media Galaxy (RO)**: Sister electronics retailer.
4. **PC Garage (RO)**: Specialized PC, workstation, and GPU stock levels (`Stoc magazin suficient`, `Stoc depozit`, `Stoc epuizat`).
5. **Flanco (RO)**: Tech & appliances retailer with in-store pickup & delivery.
6. **Auchan Hypermarket (RO)**: Live grocery & hypermarket catalog with exact inventory quantities (`AvailableQuantity`).
7. **Amazon Direct (Global/EU)**: Multi-locale support for Europe (DE/UK) and US.

---

## 🛠️ Architecture Highlights
* **Zero TLS Fingerprint Blocking**: Powered by `curl_cffi` browser impersonation (Chrome 124 TLS JA3/JA4 emulation).
* **Parallel Asynchronous Fan-Out**: Fires all store connectors concurrently via `asyncio`.
* **Server-Sent Events (SSE)**: Results stream into the UI store-by-store in milliseconds without waiting for the slowest store.
* **Top 49 Countries Registry**: Extensible adapter pattern ready for multi-national scaling.

---

## 🏁 Starting the Server
```bash
./run.sh
# or manually:
./venv/bin/python server.py
```
