#!/usr/bin/env python3
import requests
import hashlib
import time
import logging
from datetime import datetime

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"

KEYWORDS = [
    "13.6", "13/6", "יוני", "499", "499.00", "499 ₪",
]

CHECK_INTERVAL  = 60   # בדיקה כל דקה
STATUS_INTERVAL = 60   # עדכון שעתי = 60 בדיקות

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

    content = fetch_page()
    if content:
        sees_content = '499' in content or '13.6' in content
        send_telegram(
            f"🎟 <b>מוניטור כרטיסים התחיל!</b>\n"
            f"🔍 מחפש: <b>13.6.26 | 499 ₪</b>\n"
            f"⏱ בודק כל דקה | עדכון שעתי\n\n"
            f"🔬 {'✅ הדף נקרא תקין' if sees_content else '⚠️ הדף דינמי – ייתכן שלא נראה הכל'}"
        )

    check_num = 0

    while True:
        check_num += 1
        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"בדיקה #{check_num}...")

        content = fetch_page()
        if content is None:
            time.sleep(CHECK_INTERVAL)
            continue

        found = check_keywords(content)

        if found:
            # התראה מיידית!
            log.info(f"🚨 נמצאו כרטיסים: {found}")
            send_telegram(
                f"🚨 <b>נמצאו כרטיסים לתאריך 13.6!</b>\n"
                f"💰 מחיר: 499 ₪\n"
                f"🔍 נמצא: {', '.join(found)}\n"
                f"🕐 {now}\n\n"
                f"👉 <a href='{TARGET_URL}'>לחץ לרכישה עכשיו!</a>"
            )
        elif check_num % STATUS_INTERVAL == 0:
            # עדכון שעתי בלבד
            log.info("עדכון שעתי – אין כרטיסים")
            send_telegram(
                f"✅ <b>עדכון שעתי</b>\n"
                f"בדקתי {check_num} פעמים – אין עדיין כרטיסים ל-13.6 / 499₪\n"
                f"🕐 {now} | ממשיך לעקוב... 👀"
            )
        else:
            log.info("אין שינויים רלוונטיים")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
