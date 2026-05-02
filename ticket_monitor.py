#!/usr/bin/env python3
import time
import random
import logging
import json
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"

CHECK_INTERVAL   = 60       # שניות בסיס בין בדיקות
RANDOM_EXTRA     = 30       # שניות אקראיות נוספות
STATUS_EVERY_SEC = 3600     # עדכון שעתי אמיתי
MAX_ERRORS       = 5        # כמה שגיאות רצופות לפני התראה

# פורמטים אפשריים של התאריך – נרחיב לפי מה שנראה באבחון
DATE_VARIANTS  = ["13/6", "13.6", "13/06", "13 ביוני", "יוני 13",
                  "june 13", "jun 13", "2026-06-13", "06-13", "6/13"]
PRICE_TARGET   = 499

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


def search_json_recursive(obj, depth=0):
    """מחפש רקורסיבית ב-JSON אחר מחיר 499 ותאריך 13/6"""
    if depth > 10:
        return False, False
    
    date_found  = False
    price_found = False
    
    if isinstance(obj, dict):
        text = json.dumps(obj, ensure_ascii=False).lower()
        for v in DATE_VARIANTS:
            if v.lower() in text:
                date_found = True
                break
        if str(PRICE_TARGET) in text:
            price_found = True
        for val in obj.values():
            d, p = search_json_recursive(val, depth + 1)
            date_found  = date_found  or d
            price_found = price_found or p

    elif isinstance(obj, list):
        for item in obj:
            d, p = search_json_recursive(item, depth + 1)
            date_found  = date_found  or d
            price_found = price_found or p

    elif isinstance(obj, str):
        lower = obj.lower()
        for v in DATE_VARIANTS:
            if v.lower() in lower:
                date_found = True
                break
        if str(PRICE_TARGET) in obj:
            price_found = True

    elif isinstance(obj, (int, float)):
        if obj == PRICE_TARGET:
            price_found = True

    return date_found, price_found


def check_page():
    api_jsons   = []
    api_texts   = []
    browser     = None

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            def handle_response(response):
                try:
                    url = response.url.lower()
                    if any(x in url for x in ["api", "seat", "ticket", "present",
                                               "event", "price", "booking", "kupat"]):
                        body = response.text()
                        api_texts.append(body[:3000])
                        try:
                            api_jsons.append(json.loads(body))
                        except:
                            pass
                except:
                    pass

            page.on("response", handle_response)

            try:
                page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            except PlaywrightTimeout:
                log.warning("Timeout בטעינה, ממשיך עם מה שיש...")

            time.sleep(10)  # המתן לטעינת JS

            page_text   = page.inner_text("body")
            page_source = page.content()

        finally:
            if browser:
                browser.close()

    # --- חיפוש ב-JSON (הכי אמין) ---
    json_date_found  = False
    json_price_found = False
    for j in api_jsons:
        d, p = search_json_recursive(j)
        json_date_found  = json_date_found  or d
        json_price_found = json_price_found or p

    # --- חיפוש בטקסט כגיבוי ---
    all_text = page_text + page_source + " ".join(api_texts)
    text_date_found  = any(v.lower() in all_text.lower() for v in DATE_VARIANTS)
    text_price_found = str(PRICE_TARGET) in all_text

    date_found  = json_date_found  or text_date_found
    price_found = json_price_found or text_price_found
    avail_found = any(v.lower() in page_text.lower()
                      for v in ["זמין", "פנוי", "הוסף לסל", "רכוש", "available", "add to cart"])

    return {
        "relevant":         date_found and price_found,
        "date_found":       date_found,
        "price_found":      price_found,
        "avail_found":      avail_found,
        "api_count":        len(api_texts),
        "json_count":       len(api_jsons),
        "json_date":        json_date_found,
        "json_price":       json_price_found,
        "text_sample":      page_text[:400],
    }


def main():
    log.info("מוניטור מתחיל – גרסה מקיפה...")
    send_telegram(
        "🎟 <b>מוניטור כרטיסים – גרסה מקיפה!</b>\n"
        "🔍 מחפש: <b>13.6.26 AND 499 ₪</b>\n"
        "⏱ בודק כל ~דקה | עדכון כל שעה\n"
        "🔎 חיפוש ב-JSON + טקסט + API\n\n"
        "⏳ בדיקת תקינות ראשונה..."
    )

    # --- בדיקת תקינות ראשונה ---
    try:
        result = check_page()
        send_telegram(
            f"🔬 <b>בדיקת תקינות:</b>\n"
            f"📅 תאריך 13/6: {'✅' if result['date_found'] else '❌'} "
            f"({'JSON' if result['json_date'] else 'טקסט' if result['date_found'] else 'לא נמצא'})\n"
            f"💰 מחיר 499: {'✅' if result['price_found'] else '❌'} "
            f"({'JSON' if result['json_price'] else 'טקסט' if result['price_found'] else 'לא נמצא'})\n"
            f"🟢 זמינות: {'✅' if result['avail_found'] else '❌'}\n"
            f"🌐 API: {result['api_count']} תגובות ({result['json_count']} JSON)\n\n"
            f"📄 <b>טקסט מהדף:</b>\n<code>{result['text_sample'][:300]}</code>\n\n"
            f"<i>{'⚠️ כרטיסים נמצאו כבר!' if result['relevant'] else 'הבוט פעיל ומחכה לכרטיסים 👀'}</i>"
        )
    except Exception as e:
        send_telegram(f"⚠️ שגיאה בבדיקת תקינות: {e}")

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
            result = check_page()
            error_streak = 0  # אפס שגיאות רצופות

            if result["relevant"] and not last_found:
                log.info("🚨 נמצאו כרטיסים!")
                send_telegram(
                    f"🚨 <b>נמצאו כרטיסים לתאריך 13.6 במחיר 499₪!</b>\n"
                    f"🟢 זמין: {'✅ כן!' if result['avail_found'] else '⚠️ בדוק'}\n"
                    f"🕐 {now}\n\n"
                    f"👉 <a href='{TARGET_URL}'>לחץ לרכישה עכשיו!</a>"
                )
                last_found = True

            elif not result["relevant"] and last_found:
                send_telegram(
                    f"ℹ️ <b>הכרטיסים נעלמו</b>\n"
                    f"🕐 {now}\n"
                    f"ממשיך לעקוב... 👀"
                )
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
                send_telegram(
                    f"⚠️ <b>{MAX_ERRORS} שגיאות רצופות!</b>\n"
                    f"שגיאה אחרונה: {str(e)[:200]}\n"
                    f"הבוט ממשיך לנסות..."
                )
                error_streak = 0  # אפס כדי לא לספאם


if __name__ == "__main__":
    main()
