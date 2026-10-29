import time
import uuid
import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from core.schema import RestockAlert

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
ALERTS_FILE = os.path.join(DATA_DIR, "alerts_db.json")
LEGACY_ALERTS_FILE = os.path.join(os.path.dirname(__file__), "..", "alerts_db.json")

class AlertManager:
    def __init__(self):
        self.alerts: Dict[str, RestockAlert] = {}
        self._load()

    def _load(self):
        file_to_load = None
        if os.path.isfile(ALERTS_FILE):
            file_to_load = ALERTS_FILE
        elif os.path.isfile(LEGACY_ALERTS_FILE):
            file_to_load = LEGACY_ALERTS_FILE

        if file_to_load:
            try:
                with open(file_to_load, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        alert = RestockAlert(**item)
                        self.alerts[alert.id] = alert
            except Exception as e:
                print(f"[AlertManager] Error loading alerts: {e}")

    def _save(self):
        try:
            with open(ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump([a.model_dump() for a in self.alerts.values()], f, indent=2)
        except Exception as e:
            print(f"[AlertManager] Error saving alerts: {e}")

    def create_alert(
        self,
        query: str,
        store_name: str,
        target_price: Optional[float] = None,
        email: Optional[str] = None,
        product_title: Optional[str] = None,
        product_url: Optional[str] = None
    ) -> RestockAlert:
        alert_id = f"alt_{uuid.uuid4().hex[:8]}"
        alert = RestockAlert(
            id=alert_id,
            query=query,
            store_name=store_name,
            target_price=target_price,
            email=email or "user@example.com",
            product_title=product_title or query,
            product_url=product_url,
            is_triggered=False,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            last_status="Out of Stock",
            last_checked=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self.alerts[alert_id] = alert
        self._save()
        return alert

    def get_all_alerts(self) -> List[RestockAlert]:
        return list(self.alerts.values())

    def delete_alert(self, alert_id: str) -> bool:
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save()
            return True
        return False

    def mark_triggered(self, alert_id: str, new_price: float):
        if alert_id in self.alerts:
            self.alerts[alert_id].is_triggered = True
            self.alerts[alert_id].last_status = "IN STOCK NOW!"
            self.alerts[alert_id].last_checked = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._save()
