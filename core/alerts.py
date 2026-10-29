import time
import uuid
import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from core.schema import RestockAlert
from core.db import get_database_adapter

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
ALERTS_FILE = os.path.join(DATA_DIR, "alerts_db.json")
LEGACY_ALERTS_FILE = os.path.join(os.path.dirname(__file__), "..", "alerts_db.json")

class AlertManager:
    def __init__(self):
        self.alerts: Dict[str, RestockAlert] = {}
        try:
            self.db_adapter = get_database_adapter()
        except Exception:
            self.db_adapter = None
        self._load()

    def _load(self):
        # 1. Try loading from database adapter first
        if self.db_adapter:
            try:
                db_alerts = self.db_adapter.get_alerts()
                if db_alerts:
                    for a in db_alerts:
                        self.alerts[a.id] = a
                    return
            except Exception as e:
                print(f"[AlertManager] Error loading alerts from DB: {e}")

        # 2. Fallback to JSON file if DB has no alerts or isn't ready
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
                        # Mirror to database
                        if self.db_adapter:
                            try:
                                self.db_adapter.save_alert(alert)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[AlertManager] Error loading alerts: {e}")

    def _save(self):
        # 1. Save to JSON file
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
        if self.db_adapter:
            try:
                self.db_adapter.save_alert(alert)
            except Exception as e:
                print(f"[AlertManager] Error persisting alert to DB: {e}")
        self._save()
        return alert

    def get_all_alerts(self) -> List[RestockAlert]:
        return list(self.alerts.values())

    def delete_alert(self, alert_id: str) -> bool:
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            if self.db_adapter:
                try:
                    self.db_adapter.delete_alert(alert_id)
                except Exception:
                    pass
            self._save()
            return True
        return False

    def mark_triggered(self, alert_id: str, new_price: float):
        if alert_id in self.alerts:
            self.alerts[alert_id].is_triggered = True
            self.alerts[alert_id].last_status = "IN STOCK NOW!"
            self.alerts[alert_id].last_checked = datetime.now().strftime("%Y-%m-%d %H:%M")
            if self.db_adapter:
                try:
                    self.db_adapter.save_alert(self.alerts[alert_id])
                except Exception:
                    pass
            self._save()
