#!/usr/bin/env python3
import time
import random
import logging
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"

CHECK_INTERVAL   = 60
RANDOM_EXTRA     = 30
STATUS_EVERY_SEC = 3600
MAX_ERRORS       = 5

DATE_VARIANTS = ["13/6", "13.6", "13/06", "13 ביוני", "יוני 13",
                 "june 13", "jun 13", "2026-06-13", "06-13"]
PRICE_TARGET  = 499

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


def both_in_same_response(api_texts):
    for text in api_texts:
        has_date  = any(v.lower() in text.lower() for v in DATE_VARIANTS)
        has_price = str(PRICE_TARGET) in text
        if has_date and has_price:
            return True
    return False


def check_page():
    api_texts  = []
    playwright = None
    browser    = None

    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        def handle_response(response):
            try:
                if any(x in response.url.lower() for x in
                       ["api", "seat", "ticket", "present", "event",
                        "price", "booking", "kupat", "feature"]):
                    body = response.text()
                    if body and len(body) > 10:
                        api_texts.append(body[:5000])
            except:
                pass

        page.on("response", handle_response)

        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeout:
            log.warning("Timeout בטעינה, ממשיך...")

        time.sleep(10)

        # שימוש ב-evaluate במקום inner_text – לא תוקף
        try:
            page_text = page.evaluate("document.body.innerText") or ""
        except:
            page_text = ""

        try:
            page_source = page.content() or ""
        except:
            page_source = ""

        # הוסף גם טקסט הדף לרשימת התגובות לחיפוש
        if page_text or page_source:
            api_texts.append(page_text + page_source)

    finally:
        try:
            if browser:    browser.close()
        except: pass
        try:
            if playwright: playwright.stop()
        except: pass

    return {
        "relevant":  both_in_same_response(api_texts),
        "api_count": len(api_texts),
    }


def main():
    log.info("מוניטור מתחיל...")
    send_telegram(
        "🎟 <b>מוניטור כרטיסים התחיל!</b>\n"
        "🔍 מחפש: <b>13.6 AND 499₪ – באותה תגובה</b>\n"
        "⏱ בודק כל ~דקה | עדכון כל שעה\n\n"
        "⏳ בדיקת תקינות..."
    )

    try:
        result = check_page()
        send_telegram(
            f"🔬 <b>בדיקת תקינות:</b>\n"
            f"🎯 13.6 + 499 באותה תגובה: {'✅ נמצא!' if result['relevant'] else '❌ לא נמצא (תקין – אין כרטיסים)'}\n"
            f"🌐 תגובות API: {result['api_count']}\n\n"
            f"<i>הבוט פעיל ומחכה לכרטיסים 👀</i>"
        )
    except Exception as e:
        send_telegram(f"⚠️ שגיאה בתקינות: {e}")

    check_num        = 0
    last_found       = False
    last_status_time = time.time()
    error_streak     = 0

    while True:
        check_num += 1
        wait = CHECK_INTERVAL + random.randint(0, RANDOM_EXTRA)
        log.info(f"ממתין {wait} שניות...")
        time.sleep(wait)

        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"בדיקה #{check_num} ({now})...")

        try:
            result       = check_page()
            error_streak = 0

            if result["relevant"] and not last_found:
                send_telegram(
                    f"🚨 <b>נמצאו כרטיסים לתאריך 13.6 במחיר 499₪!</b>\n"
                    f"🕐 {now}\n\n"
                    f"👉 <a href='{TARGET_URL}'>לחץ לרכישה עכשיו!</a>"
                )
                last_found = True

            elif not result["relevant"] and last_found:
                send_telegram(f"ℹ️ הכרטיסים נעלמו\n🕐 {now}\nממשיך... 👀")
                last_found = False

            elif time.time() - last_status_time >= STATUS_EVERY_SEC:
                send_telegram(
                    f"✅ <b>עדכון שעתי</b>\n"
                    f"בדקתי {check_num} פעמים – אין עדיין כרטיסים ל-13.6 / 499₪\n"
                    f"🕐 {now} | ממשיך לעקוב... 👀"
                )
                last_status_time = time.time()
            else:
                log.info("אין שינויים")

        except Exception as e:
            error_streak += 1
            log.error(f"שגיאה #{error_streak}: {e}")
            if error_streak >= MAX_ERRORS:
                send_telegram(f"⚠️ <b>{MAX_ERRORS} שגיאות רצופות!</b>\n{str(e)[:200]}")
                error_streak = 0


if __name__ == "__main__":
    main()
