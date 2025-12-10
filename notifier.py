import requests
import os
from dotenv import load_dotenv

load_dotenv()
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
TG_CHANNEL = os.getenv('TELEGRAM_CHANNEL_ID')
DISCORD_URL = os.getenv('DISCORD_WEBHOOK_URL')

def send_public_message(text, msg_type="INFO"):
    # Telegram Channel
    if TG_TOKEN and TG_CHANNEL:
        try:
            icon = "ℹ️"
            if msg_type == "BUY": icon = "🚀"
            elif msg_type == "PROFIT": icon = "🟢"
            elif msg_type == "LOSS": icon = "🔴"
            
            requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                         params={'chat_id': TG_CHANNEL, 'text': f"{icon} {text}", 'parse_mode': 'Markdown'}, timeout=2)
        except: pass
    
    # Discord Webhook
    if DISCORD_URL:
        try:
            color = 3447003
            if msg_type == "BUY": color = 3066993
            elif msg_type == "PROFIT": color = 5763719
            elif msg_type == "LOSS": color = 15158332
            
            payload = {"embeds": [{"description": text.replace('*','').replace('`',''), "color": color}]}
            requests.post(DISCORD_URL, json=payload, timeout=2)
        except: pass
