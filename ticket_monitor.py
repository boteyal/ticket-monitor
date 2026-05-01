#!/usr/bin/env python3
import time
import logging
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"

KEYWORDS = ["13.6", "13/6", "499", "499.00", "499 ₪"]

CHECK_INTERVAL  = 60
STATUS_INTERVAL = 60

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


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = webdriver.Chrome(options=options)
    return driver


def fetch_page_content():
    driver = None
    try:
        driver = get_driver()
        driver.get(TARGET_URL)
        time.sleep(5)  # המתן לטעינת JavaScript
        content = driver.page_source
        return content
    except Exception as e:
        log.error(f"שגיאת דפדפן: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def check_keywords(content):
    lower = content.lower()
    return [kw for kw in KEYWORDS if kw.lower() in lower]


def main():
    log.info("מוניטור מתחיל עם Selenium...")

    send_telegram(
        "🎟 <b>מוניטור כרטיסים התחיל! (גרסה מתקדמת)</b>\n"
        "🔍 מחפש: <b>13.6.26 | 499 ₪</b>\n"
        "⏱ בודק כל דקה | עדכון שעתי\n"
        "🌐 משתמש בדפדפן אמיתי – רואה את כל התוכן"
    )

    check_num = 0

    while True:
        check_num += 1
        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"בדיקה #{check_num}...")

        content = fetch_page_content()
        if content is None:
            log.warning("לא הצלחתי לטעון, מנסה שוב")
            time.sleep(CHECK_INTERVAL)
            continue

        found = check_keywords(content)

        if found:
            log.info(f"🚨 נמצאו כרטיסים: {found}")
            send_telegram(
                f"🚨 <b>נמצאו כרטיסים לתאריך 13.6!</b>\n"
                f"💰 מחיר: 499 ₪\n"
                f"🔍 נמצא: {', '.join(found)}\n"
                f"🕐 {now}\n\n"
                f"👉 <a href='{TARGET_URL}'>לחץ לרכישה עכשיו!</a>"
            )
        elif check_num % STATUS_INTERVAL == 0:
            log.info("עדכון שעתי")
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
