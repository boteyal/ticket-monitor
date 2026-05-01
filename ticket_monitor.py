#!/usr/bin/env python3
import time
import random
import logging
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"

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


def check_page():
    api_responses = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # תפוס תשובות API
        def handle_response(response):
            try:
                url = response.url
                if any(x in url for x in ["api", "seat", "ticket", "present", "event", "price", "availab"]):
                    try:
                        body = response.text()
                        api_responses.append({"url": url, "body": body[:500]})
                    except:
                        api_responses.append({"url": url, "body": ""})
            except:
                pass

        page.on("response", handle_response)

        # השינוי שעשינו: מחכים רק לטעינת המבנה המרכזי כדי למנוע קריסת Timeout
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        content = page.content()
        text = page.inner_text("body")

        browser.close()

    # בדיקת תאריך
    date_found = any(v in text or v in content for v in ["13/6", "13.6", "13 ביוני", "יוני 13"])

    # בדיקת מחיר – חפש ב-API responses גם
    all_text = text + content + " ".join(r["body"] for r in api_responses)
    price_found = any(v in all_text for v in ["499", "499.00"])

    # בדיקת זמינות
    available_found = any(v.lower() in text.lower() for v in ["זמין", "פנוי", "הוסף לסל", "רכוש", "available"])

    return {
        "date_found": date_found,
        "price_found": price_found,
        "available_found": available_found,
        "api_count": len(api_responses),
        "api_urls": [r["url"] for r in api_responses[:3]],
        "text_snippet": text[:200]
    }


def main():
    log.info("מוניטור Playwright מתחיל...")

    send_telegram(
        "🎟 <b>מוניטור כרטיסים – גרסה מתקדמת!</b>\n"
        "🔍 מחפש: <b>13.6.26 | 499 ₪</b>\n"
        "⏱ בודק כל דקה פלוס זמן אקראי | עדכון שעתי\n"
        "🌐 דפדפן אמיתי + יירוט API\n\n"
        "⏳ בדיקת תקינות ראשונה מתבצעת..."
    )

    # בדיקת תקינות
    try:
        result = check_page()
        send_telegram(
            f"🔬 <b>בדיקת תקינות:</b>\n"
            f"📅 תאריך 13/6: {'✅' if result['date_found'] else '❌ (אין כרטיסים עדיין – תקין)'}\n"
            f"💰 מחיר 499: {'✅' if result['price_found'] else '❌ (אין כרטיסים עדיין – תקין)'}\n"
            f"🟢 זמין: {'✅' if result['available_found'] else '❌'}\n"
            f"🌐 API נתפס: {'✅ ' + str(result['api_count']) + ' בקשות' if result['api_count'] > 0 else '❌'}\n\n"
            f"<i>הבוט פעיל ומחכה לכרטיסים 👀</i>"
        )
    except Exception as e:
        send_telegram(f"⚠️ שגיאה בבדיקת תקינות: {e}")

    check_num = 0
    last_found = False

    while True:
        check_num += 1
        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"בדיקה #{check_num}...")

        try:
            result = check_page()
            tickets_found = result["date_found"] or result["price_found"]

            if tickets_found and not last_found:
                log.info("🚨 נמצאו כרטיסים!")
                send_telegram(
                    f"🚨 <b>נמצאו כרטיסים לתאריך 13.6!</b>\n"
                    f"💰 מחיר: 499 ₪\n"
                    f"🟢 זמין לרכישה: {'✅ כן!' if result['available_found'] else '⚠️ בדוק'}\n"
                    f"🕐 {now}\n\n"
                    f"👉 <a href='{TARGET_URL}'>לחץ לרכישה עכשיו!</a>"
                )
                last_found = True

            elif not tickets_found and last_found:
                send_telegram(f"ℹ️ הכרטיסים נעלמו\n🕐 {now}\nממשיך לעקוב... 👀")
                last_found = False

            elif check_num % STATUS_INTERVAL == 0:
                send_telegram(
                    f"✅ <b>עדכון שעתי</b>\n"
                    f"בדקתי {check_num} פעמים – אין עדיין כרטיסים ל-13.6 / 499₪\n"
                    f"🕐 {now} | ממשיך לעקוב... 👀"
                )
            else:
                log.info("אין שינויים")

        except Exception as e:
            log.error(f"שגיאה: {e}")

        # הוספת זמן אקראי בין 5 ל-25 שניות כדי למנוע חסימת בוטים
        time.sleep(CHECK_INTERVAL + random.randint(5, 25))


if __name__ == "__main__":
    main()
