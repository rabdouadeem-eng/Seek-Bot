# 🔍 Seek Bot - صندوق التداول المستقل
بوت تداول ورقي (Paper Trading) مع بيانات حية من Binance واستراتيجية القيعان والقمم.

## التشغيل
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
