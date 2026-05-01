# משתמשים בגרסת פייתון רשמית וקלילה
FROM python:3.11-slim

# מגדירים את תיקיית העבודה בשרת
WORKDIR /app

# מעתיקים את קובץ הדרישות
COPY requirements.txt .

# מתקינים את הספריות מתוך הקובץ
RUN pip install --no-cache-dir -r requirements.txt

# הקסם: מוריד את הדפדפן יחד עם כל ספריות הלינוקס שהוא אי פעם יצטרך
RUN playwright install --with-deps chromium

# מעתיקים את שאר הקוד
COPY . .

# הפקודה שמריצה את הבוט
CMD ["python", "ticket_monitor.py"]
