#!/usr/bin/env python3
import time
import json
import logging
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

TELEGRAM_TOKEN   = "8513099859:AAF8Pz0eqlW-_kle5FGNaUgQCS3k60gBnjw"
TELEGRAM_CHAT_ID = "8511626921"
TARGET_URL       = "https://tickets.kupat.co.il/booking/features/937?display=list&prsntId=52351"

TARGET_DATE      = "13/6"      # תאריך לחיפוש
TARGET_PRICE     = 499         # מחיר לחיפוש

CHECK_INTERVAL   = 60          # שניות בין בדיקות
STATUS_INTERVAL  = 60          # עדכון שעתי = 60 בדיקות

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
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    # יירוט רשת
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=options)
    return driver


def extract_api_data(driver):
    """מנסה לתפוס בקשות API מהרשת"""
    logs = driver.get_log("performance")
    api_data = []
    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.responseReceived":
                url = msg["params"]["response"]["url"]
                if "api" in url.lower() or "seat" in url.lower() or "ticket" in url.lower() or "present" in url.lower():
                    api_data.append(url)
        except:
            pass
    return api_data


def check_page_content(driver):
    """בודק את תוכן הדף המלא אחרי טעינת JS"""
    page_text = driver.find_element("tag name", "body").text
    page_source = driver.page_source

    results = {
        "found_date": False,
        "found_price": False,
        "found_available": False,
        "details": []
    }

    # בדיקת תאריך
    date_variants = ["13/6", "13.6", "13 ביוני", "יוני 13", "June 13"]
    for variant in date_variants:
        if variant in page_text or variant in page_source:
            results["found_date"] = True
            results["details"].append(f"תאריך: {variant}")
            break

    # בדיקת מחיר
    price_variants = ["499", "499.00", "499 ₪", "499₪"]
    for variant in price_variants:
        if variant in page_text or variant in page_source:
            results["found_price"] = True
            results["details"].append(f"מחיר: {variant}")
            break

    # בדיקת זמינות
    available_variants = ["זמין", "available", "פנוי", "הוסף לסל", "add to cart", "רכוש"]
    for variant in available_variants:
        if variant.lower() in page_text.lower():
            results["found_available"] = True
            results["details"].append(f"זמינות: {variant}")
            break

    return results, page_text[:300]


def run_check():
    driver = None
    try:
        driver = get_driver()
        driver.get(TARGET_URL)

        # המתן לטעינת הדף
        time.sleep(8)

        # תפוס API calls
        api_urls = extract_api_data(driver)
        if api_urls:
            log.info(f"API URLs שנתפסו: {api_urls[:3]}")

        # בדוק תוכן
        results, snippet = check_page_content(driver)

        return results, api_urls, snippet

    except Exception as e:
        log.error(f"שגיאה: {e}")
        return None, [], ""
    finally:
        if driver:
            driver.quit()


def main():
    log.info("מוניטור מתחיל – גרסה מתקדמת עם יירוט רשת...")

    send_telegram(
        "🎟 <b>מוניטור כרטיסים – גרסה מתקדמת!</b>\n"
        "🔍 מחפש: <b>13.6.26 | 499 ₪</b>\n"
        "⏱ בודק כל דקה | עדכון שעתי\n"
        "🌐 דפדפן אמיתי + יירוט API\n\n"
        "⏳ בדיקת תקינות ראשונה מתבצעת..."
    )

    # בדיקת תקינות ראשונה
    results, api_urls, snippet = run_check()

    if results:
        diag_msg = (
            f"🔬 <b>בדיקת תקינות:</b>\n"
            f"📅 תאריך 13/6 נמצא: {'✅' if results['found_date'] else '❌'}\n"
            f"💰 מחיר 499 נמצא: {'✅' if results['found_price'] else '❌'}\n"
            f"🟢 זמינות נמצאת: {'✅' if results['found_available'] else '❌'}\n"
        )
        if api_urls:
            diag_msg += f"🌐 API נתפס: ✅ ({len(api_urls)} בקשות)\n"
        else:
            diag_msg += "🌐 API נתפס: ❌ (לא נמצאו)\n"

        if not results['found_date'] and not results['found_price']:
            diag_msg += "\n⚠️ <i>הדף לא מציג מידע כרגע (אין כרטיסים) – זה תקין! הבוט יתריע ברגע שיופיעו.</i>"

        send_telegram(diag_msg)
    else:
        send_telegram("⚠️ שגיאה בבדיקת תקינות – מנסה שוב בדקה הבאה")

    check_num = 0
    last_state = False  # האם נמצאו כרטיסים בבדיקה הקודמת

    while True:
        check_num += 1
        now = datetime.now().strftime("%H:%M:%S")
        log.info(f"בדיקה #{check_num}...")

        results, api_urls, snippet = run_check()

        if results is None:
            log.warning("שגיאה בבדיקה, ממשיך...")
            time.sleep(CHECK_INTERVAL)
            continue

        # נמצאו כרטיסים רלוונטיים!
        tickets_found = results["found_date"] or results["found_price"]

        if tickets_found and not last_state:
            # מצב חדש – נמצאו כרטיסים!
            log.info(f"🚨 נמצאו כרטיסים!")
            details_str = "\n".join(results["details"]) if results["details"] else "שינוי בדף"
            send_telegram(
                f"🚨 <b>נמצאו כרטיסים לתאריך 13.6!</b>\n"
                f"💰 מחיר: 499 ₪\n"
                f"📋 פרטים: {details_str}\n"
                f"🟢 זמין לרכישה: {'✅ כן!' if results['found_available'] else '⚠️ בדוק'}\n"
                f"🕐 {now}\n\n"
                f"👉 <a href='{TARGET_URL}'>לחץ לרכישה עכשיו!</a>"
            )
            last_state = True

        elif not tickets_found and last_state:
            # הכרטיסים נעלמו
            log.info("כרטיסים נעלמו")
            send_telegram(
                f"ℹ️ <b>הכרטיסים שנמצאו כבר לא זמינים</b>\n"
                f"🕐 {now}\n"
                f"ממשיך לעקוב... 👀"
            )
            last_state = False

        elif check_num % STATUS_INTERVAL == 0:
            # עדכון שעתי
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
