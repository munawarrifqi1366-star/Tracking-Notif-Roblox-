import requests
import time
import threading
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- KONFIGURASI TELEGRAM ---
TELEGRAM_BOT_TOKEN = "7955453002:AAFvmfj9oWPaVfm1weNz1C1m-dzbxwioEJs"
TELEGRAM_CHAT_ID = "7376896906"

# --- KONFIGURASI TARGET ROBLOX ---
ROBLOX_USER_ID = 9465641652
ROBLOX_CHECK_INTERVAL = 15  # Cek setiap 15 detik

# --- KONFIGURASI TARGET TIKTOK ---
TARGET_TIKTOK_USERNAME = "Chica.holic"  # Username target tanpa @
TIKTOK_CHECK_INTERVAL = 300  # Cek setiap 5 menit (300 detik)
TIKTOK_STATE_FILE = f"tiktok_{TARGET_TIKTOK_USERNAME.lower()}_state.json"

STATUS_MAP = {
    0: "Offline 🔴",
    1: "Online di Website 🌐",
    2: "Sedang Bermain Game 🎮",
    3: "Sedang di Roblox Studio 🛠️"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# State lokal Roblox
last_status = None
current_map = None
current_server_id = None

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error kirim pesan Telegram: {e}")

def clean_markdown(text):
    if not text:
        return "Tidak diketahui"
    return str(text).replace("`", "'")

# --- MODUL ROBLOX TRACKER ---
def check_roblox_status():
    global last_status, current_map, current_server_id
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [ROBLOX_USER_ID]}
    roblox_headers = {"Content-Type": "application/json", "User-Agent": HEADERS["User-Agent"]}
    
    try:
        response = requests.post(url, json=payload, headers=roblox_headers, timeout=10)
        data = response.json()
        
        if "userPresences" in data and len(data["userPresences"]) > 0:
            user_data = data["userPresences"][0]
            status = user_data.get("userPresenceType", 0)
            
            new_map = "Tidak diketahui"
            new_server_id = "Tidak diketahui"
            
            if status == 2:
                if "lastLocation" in user_data and user_data["lastLocation"]:
                    new_map = clean_markdown(user_data["lastLocation"])
                else:
                    new_map = "Bermain Game (Nama Map Privat/Hidden)"
                
                if "gameId" in user_data and user_data["gameId"]:
                    new_server_id = str(user_data["gameId"])

            is_map_or_server_changed = (status == 2 and (new_map != current_map or new_server_id != current_server_id))
            
            if last_status is None:
                last_status = status
                current_map = new_map if status == 2 else None
                current_server_id = new_server_id if status == 2 else None
                return

            if status != last_status or is_map_or_server_changed:
                status_text = STATUS_MAP.get(status, "Unknown")
                
                if status == 0:
                    msg = "🔴 **TARGET ROBLOX OFFLINE!**"
                    send_telegram_msg(msg)
                    current_map = None
                    current_server_id = None

                elif status == 2:
                    current_map = new_map
                    current_server_id = new_server_id
                    
                    msg = (f"🚨 **TARGET UPDATE STATUS!**\n"
                           f"Status: Sedang Bermain Game 🎮\n"
                           f"📍 Masuk ke map: `{new_map}`\n"
                           f"ID: `{new_server_id}`")
                    send_telegram_msg(msg)

                else:
                    msg = f"🚨 **TARGET ROBLOX STATUS BERUBAH!**\nStatus: {status_text}"
                    send_telegram_msg(msg)
                    current_map = None
                    current_server_id = None

                last_status = status
            
    except Exception as e:
        print(f"Error fetch Roblox API: {e}")

def run_roblox_tracker():
    print("Bot pemantau Roblox aktif...")
    while True:
        check_roblox_status()
        time.sleep(ROBLOX_CHECK_INTERVAL)

# --- MODUL TIKTOK TRACKER ---
def load_tiktok_state():
    if os.path.exists(TIKTOK_STATE_FILE):
        try:
            with open(TIKTOK_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"following": [], "followers": []}
    return None

def save_tiktok_state(state):
    with open(TIKTOK_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def fetch_tiktok_data(username):
    url = f"https://www.tiktok.com/node/share/user/@{username}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error fetch TikTok API: {e}")
    return None

def check_tiktok_status():
    old_state = load_tiktok_state()
    raw_data = fetch_tiktok_data(TARGET_TIKTOK_USERNAME)
    
    if not raw_data or "userInfo" not in raw_data:
        return

    current_following = raw_data.get("followingList", []) 
    current_followers = raw_data.get("followerList", [])

    if old_state is None:
        save_tiktok_state({
            "following": current_following,
            "followers": current_followers
        })
        send_telegram_msg(f"✅ **BOT TRACKER TIKTOK AKTIF!**\nMemantau target: `@{TARGET_TIKTOK_USERNAME}` (Setiap 5 Menit)")
        return

    old_following = set(old_state.get("following", []))
    old_followers = set(old_state.get("followers", []))

    new_following = set(current_following) - old_following
    new_followers = set(current_followers) - old_followers

    for user in new_following:
        msg = (f"🚨 **TIKTOK: TARGET FOLLOW AKUN BARU!**\n\n"
               f"👤 Target: `@{TARGET_TIKTOK_USERNAME}`\n"
               f"➕ Baru mem-follow: `@{user}`\n"
               f"🔗 Link: https://www.tiktok.com/@{user}")
        send_telegram_msg(msg)

    for user in new_followers:
        msg = (f"🚨 **TIKTOK: FOLLOWER BARU TARGET!**\n\n"
               f"👤 Target: `@{TARGET_TIKTOK_USERNAME}`\n"
               f"👥 Di-follow oleh: `@{user}`\n"
               f"🔗 Link: https://www.tiktok.com/@{user}")
        send_telegram_msg(msg)

    save_tiktok_state({
        "following": list(current_following),
        "followers": list(current_followers)
    })

def run_tiktok_tracker():
    print("Bot pemantau TikTok aktif...")
    while True:
        check_tiktok_status()
        time.sleep(TIKTOK_CHECK_INTERVAL)

# Menjalankan pemantau Roblox & TikTok di thread terpisah
threading.Thread(target=run_roblox_tracker, daemon=True).start()
threading.Thread(target=run_tiktok_tracker, daemon=True).start()

# Web Server sederhana untuk Web Service Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Roblox & TikTok Multi-Tracker Running!")

server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
server.serve_forever()
