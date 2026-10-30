import asyncio
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from core.db import get_database_adapter
from core.alerts import AlertManager

async def run_alert_check_cycle():
    """
    Checks stored alerts against newly cached products in the database.
    If an alert query has matching in-stock products under the target price,
    it triggers the alert and sends an email notification if SMTP is configured.
    """
    try:
        adapter = get_database_adapter()
        manager = AlertManager()
        alerts = manager.get_all_alerts()
        untriggered = [a for a in alerts if not a.is_triggered]
        if not untriggered:
            return

        smtp_host = os.environ.get("SMTP_HOST", "").strip()
        smtp_user = os.environ.get("SMTP_USER", "").strip()
        smtp_pass = os.environ.get("SMTP_PASSWORD", "").replace(" ", "").strip()
        smtp_port = int(str(os.environ.get("SMTP_PORT", 587)).strip())
        smtp_from = os.environ.get("SMTP_FROM", smtp_user or "alerts@storestock.app").strip()

        for alert in untriggered:
            # Check cached products matching this query
            cached = adapter.get_cached_products(alert.query, country_code="RO")
            in_stock_candidates = [
                p for p in cached 
                if p.in_stock and (alert.store_name == "All Stores" or p.store_name.lower() == alert.store_name.lower())
            ]

            if alert.target_price and alert.target_price > 0:
                in_stock_candidates = [p for p in in_stock_candidates if p.price > 0 and p.price <= alert.target_price]

            if in_stock_candidates:
                best_match = in_stock_candidates[0]
                manager.mark_triggered(alert.id, best_match.price)
                print(f"[RestockAlert] Alert {alert.id} TRIGGERED for '{alert.query}' at {best_match.store_name} ({best_match.price} {best_match.currency})")

                # Send email notification if configured
                if smtp_host and smtp_user and smtp_pass and alert.email and "@" in alert.email and "example.com" not in alert.email:
                    try:
                        msg = EmailMessage()
                        msg["Subject"] = f"🔔 [StoreStock Alert] {alert.query} is IN STOCK!"
                        msg["From"] = smtp_from
                        msg["To"] = alert.email
                        body = f"""StoreStock Restock Alert Triggered!

Product: {alert.product_title or alert.query}
Store: {best_match.store_name}
Current Price: {best_match.price} {best_match.currency}
Link: {best_match.product_url}

Status: IN STOCK NOW!
Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                        msg.set_content(body)
                        import ssl
                        ssl_context = ssl.create_default_context()
                        if smtp_port == 465:
                            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl_context, timeout=10) as s:
                                s.login(smtp_user, smtp_pass)
                                s.send_message(msg)
                        else:
                            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                                s.ehlo()
                                s.starttls(context=ssl_context)
                                s.ehlo()
                                s.login(smtp_user, smtp_pass)
                                s.send_message(msg)
                        print(f"[RestockAlert] Dispatched restock email to {alert.email}")
                    except Exception as err:
                        print(f"[RestockAlert] Failed to send email to {alert.email}: {err}")

    except Exception as e:
        print(f"[RestockAlert] Error in alert check cycle: {e}")

async def background_alert_watcher(interval_seconds: int = 600):
    """Periodically checks alerts in background every 10 minutes."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await run_alert_check_cycle()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[RestockAlert] Watcher loop error: {e}")
