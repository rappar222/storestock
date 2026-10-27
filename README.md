# 🏪 StoreStock — Real-Time Multi-Store Inventory & Store Map Engine

StoreStock is a high-performance inventory search engine and physical shelf tracker. Search any product—from enterprise hardware (**NVIDIA RTX A6000 / 5090**) to daily **groceries & essentials**—and StoreStock queries live retailer APIs and physical branches in parallel.

---

## ✨ Features

- **⚡ Sub-Second Parallel Fan-Out:** Queries eMAG, Altex, Media Galaxy, PC Garage, Flanco, evoMAG, Auchan, Glovo, and Amazon simultaneously via `asyncio`.
- **📍 Physical Store Shelf Stock & OpenStreetMap:** Automatically calculates driving distances (in km) to nearby retail branches and plots in-stock shelf items on Leaflet OpenStreetMap (zero API key required).
- **🤖 AI Intent & Semantic Disambiguation:** Distinguishes standalone discrete graphics cards from 250,000+ RON prebuilt server racks and demotes cables/accessories.
- **🔔 Restock Watchlist & Background Monitoring:** Set target price ceilings and receive instant restock alerts via `/api/alerts`.
- **🛡️ Anti-Bot & TLS Impersonation:** Built with `curl_cffi` using Chrome 124 JA3/JA4 fingerprint emulation to bypass Cloudflare/Akamai bot detection.

---

## 🐳 Quick Start with Docker (Recommended)

### Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-username/storestock.git
cd storestock

# Build and start in detached mode
docker compose up -d --build
```

The app will be available at **http://localhost:3000**.

To view logs or stop:
```bash
docker compose logs -f
docker compose down
```

### Using Standard Docker CLI

```bash
# Build the Docker image
docker build -t storestock .

# Run container on port 3000
docker run -d --name storestock -p 3000:3000 --restart unless-stopped storestock
```

---

## 💻 Local Development (Without Docker)

### Prerequisites
- Python 3.10+
- Linux / macOS / WSL2

```bash
# Set up virtual environment and run
bash run.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

---

## 🔌 API Endpoints

- **Live UI:** `http://localhost:3000`
- **SSE Real-time Stream:** `GET /api/stream?q={query}&country={country_code}&lat={lat}&lon={lon}`
- **JSON Search:** `GET /api/search?q={query}&country={country_code}&lat={lat}&lon={lon}`
- **Restock Alerts:** `GET /api/alerts` | `POST /api/alerts` | `DELETE /api/alerts/{id}`
- **Supported Countries:** `GET /api/countries`

---

## 📄 License
MIT License
