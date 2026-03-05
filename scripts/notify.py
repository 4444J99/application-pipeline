#!/usr/bin/env python3
"""Notification dispatcher — routes pipeline events to configured channels.

Supports webhook (POST JSON) and email (SMTP) delivery. Events are routed
based on configuration in strategy/notifications.yaml.

Usage:
    python scripts/notify.py --config           # Show current config
    python scripts/notify.py --test-webhook     # Test webhook delivery
    python scripts/notify.py --test-email       # Test email delivery
"""

import argparse
import json
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "strategy" / "notifications.yaml"

# Event types that can trigger notifications
VALID_EVENTS = {
    "weekly_brief",
    "agent_action",
    "deadline_alert",
    "outcome_received",
    "triage_report",
}


def load_config() -> dict:
    """Load notification config from strategy/notifications.yaml."""
    if not CONFIG_PATH.exists():
        return {"webhooks": [], "email": {}, "subscriptions": {}}
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f) or {}
    return data


def dispatch_webhook(payload: dict, url: str) -> tuple[bool, str]:
    """POST JSON payload to a webhook URL. Returns (success, message)."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.URLError as e:
        return False, f"Webhook failed: {e}"
    except Exception as e:
        return False, f"Webhook error: {e}"


def dispatch_email(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    """Send email via SMTP. Loads credentials from config."""
    config = load_config()
    email_cfg = config.get("email", {})
    smtp_host = email_cfg.get("smtp_host", "")
    smtp_port = email_cfg.get("smtp_port", 587)
    sender = email_cfg.get("sender", "")
    password = email_cfg.get("password", "")  # allow-secret — reads from config, not hardcoded

    if not smtp_host or not sender:
        return False, "Email not configured (missing smtp_host or sender)"

    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=context)
            if password:
                server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        return True, f"Email sent to {', '.join(recipients)}"
    except Exception as e:
        return False, f"Email failed: {e}"


def dispatch_event(event_type: str, payload: dict) -> list[dict]:
    """Route an event to all configured channels. Returns list of results."""
    if event_type not in VALID_EVENTS:
        return [{"channel": "none", "success": False, "message": f"Unknown event type: {event_type}"}]

    config = load_config()
    subscriptions = config.get("subscriptions", {})
    channels = subscriptions.get(event_type, [])
    results = []

    enriched_payload = {
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        **payload,
    }

    for channel in channels:
        if channel == "webhook":
            for url in config.get("webhooks", []):
                ok, msg = dispatch_webhook(enriched_payload, url)
                results.append({"channel": "webhook", "url": url, "success": ok, "message": msg})
        elif channel == "email":
            recipients = config.get("email", {}).get("recipients", [])
            if recipients:
                subject = f"[Pipeline] {event_type}: {payload.get('summary', '')}"
                body = json.dumps(enriched_payload, indent=2, default=str)
                ok, msg = dispatch_email(subject, body, recipients)
                results.append({"channel": "email", "success": ok, "message": msg})

    if not results:
        results.append({"channel": "none", "success": True, "message": "No channels configured for this event"})

    return results


def show_config():
    """Display current notification configuration."""
    config = load_config()
    print("Notification Configuration")
    print("=" * 50)
    webhooks = config.get("webhooks", [])
    print(f"\n  Webhooks: {len(webhooks)}")
    for url in webhooks:
        print(f"    - {url}")

    email = config.get("email", {})
    print(f"\n  Email SMTP: {email.get('smtp_host', '(not configured)')}")
    print(f"  Email sender: {email.get('sender', '(not configured)')}")
    recipients = email.get("recipients", [])
    print(f"  Recipients: {len(recipients)}")
    for r in recipients:
        print(f"    - {r}")

    subs = config.get("subscriptions", {})
    print("\n  Event subscriptions:")
    for event in sorted(VALID_EVENTS):
        channels = subs.get(event, [])
        print(f"    {event:<25s} → {', '.join(channels) if channels else '(none)'}")


def main():
    parser = argparse.ArgumentParser(description="Pipeline notification dispatcher")
    parser.add_argument("--config", action="store_true", help="Show current configuration")
    parser.add_argument("--test-webhook", action="store_true", help="Send test webhook")
    parser.add_argument("--test-email", action="store_true", help="Send test email")
    args = parser.parse_args()

    if args.test_webhook:
        config = load_config()
        for url in config.get("webhooks", []):
            ok, msg = dispatch_webhook({"test": True, "timestamp": datetime.now().isoformat()}, url)
            print(f"  Webhook {url}: {'OK' if ok else 'FAILED'} — {msg}")
        if not config.get("webhooks"):
            print("  No webhooks configured.")
        return

    if args.test_email:
        config = load_config()
        recipients = config.get("email", {}).get("recipients", [])
        if recipients:
            ok, msg = dispatch_email("Pipeline Test", "This is a test notification.", recipients)
            print(f"  Email: {'OK' if ok else 'FAILED'} — {msg}")
        else:
            print("  No email recipients configured.")
        return

    show_config()


if __name__ == "__main__":
    main()
