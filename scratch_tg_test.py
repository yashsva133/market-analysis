import httpx
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"Token: {token[:10]}... Chat ID: {chat_id}")

client = httpx.Client(timeout=10)

# 1. getMe
me_resp = client.get(f"https://api.telegram.org/bot{token}/getMe")
print("getMe status:", me_resp.status_code, me_resp.json())

# 2. getUpdates
updates_resp = client.get(f"https://api.telegram.org/bot{token}/getUpdates")
print("getUpdates status:", updates_resp.status_code, updates_resp.json())

# 3. sendMessage test
send_resp = client.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={
        "chat_id": chat_id,
        "text": "*Market Intelligence Test Alert*\n\nSystem: Online\nTracking Universe: 5,182 companies\nTelegram Dispatch: Active",
        "parse_mode": "Markdown"
    }
)
print("sendMessage status:", send_resp.status_code, send_resp.text)
