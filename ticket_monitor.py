#!/usr/bin/env python3
import requests
import hashlib
import time
import logging
from datetime import datetime

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"
KEYWORDS         = ["זמין", "כרטיסים", "available", "ticket", "פנוי", "הוסף לסל"]
CHECK_INTERVAL   = 60  # שניות בין בדיקות

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        log.error(f"שגיאת טלגרם: {e}")
        return False


def fetch_page():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(TARGET_URL, headers=headers, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.error(f"שגיאת טעינה: {e}")
        return None


def page_hash(content):
    return hashlib.md5(content.encode()).hexdigest()


def check_keywords(content):
    lower = content.lower()
    return [kw for kw in KEYWORDS if kw.lower() in lower]


def main():
    log.info("מוניטור מתחיל...")
    send_telegram("🎟 <b>מוניטור כרטיסים התחיל!</b>\nאבדוק כל דקה ואתריע אם משהו משתנה.")

    last_hash = None
    check_num = 0

    while True:
        check_num += 1
        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"בדיקה #{check_num}...")

        content = fetch_page()
        if content is None:
            time.sleep(CHECK_INTERVAL)
            continue

        current_hash = page_hash(content)

        if last_hash is not None and current_hash != last_hash:
            log.info("תוכן הדף השתנה!")
            send_telegram(
                f"⚠️ <b>תוכן הדף השתנה!</b>\n"
                f"🕐 {now}\n\n"
                f"👉 <a href='{TARGET_URL}'>לחץ לפתיחת הדף</a>"
            )

        found = check_keywords(content)
        if found:
            log.info(f"נמצאו מילות מפתח: {found}")
            send_telegram(
                f"🎉 <b>נמצאו כרטיסים!</b>\n"
                f"🔍 מילות מפתח: {', '.join(found)}\n"
                f"🕐 {now}\n\n"
                f"👉 <a href='{TARGET_URL}'>לחץ לפתיחת הדף</a>"
            )
        else:
            log.info("לא נמצאו שינויים")

        last_hash = current_hash
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
