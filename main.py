import requests
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- KONFIGURASI ---
TELEGRAM_BOT_TOKEN = "7955453002:AAFvmfj9oWPaVfm1weNz1C1m-dzbxwioEJs"
TELEGRAM_CHAT_ID = "7376896906"
ROBLOX_USER_ID = 9465641652  # User ID target
CHECK_INTERVAL = 15  # Cek setiap 15 detik

STATUS_MAP = {
    0: "Offline 🔴",
    1: "Online di Website 🌐",
    2: "Sedang Bermain Game 🎮",
    3: "Sedang di Roblox Studio 🛠️"
}

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Menyimpan state terakhir
last_status = None
current_map = None
current_server_id = None

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error kirim pesan: {e}")

def clean_markdown(text):
    """Menghindari error parse Markdown Telegram"""
    if not text:
        return "Tidak diketahui"
    return str(text).replace("`", "'")

def check_roblox_status():
    global last_status, current_map, current_server_id
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [ROBLOX_USER_ID]}
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
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

            # Cek apakah ada perubahan status, map, atau server ID
            is_map_or_server_changed = (status == 2 and (new_map != current_map or new_server_id != current_server_id))
            
            # Abaikan saat pertama kali bot baru menyala agar tidak spam, langsung set state awal
            if last_status is None:
                last_status = status
                current_map = new_map if status == 2 else None
                current_server_id = new_server_id if status == 2 else None
                return

            # Jika terjadi perubahan status / map / server
            if status != last_status or is_map_or_server_changed:
                status_text = STATUS_MAP.get(status, "Unknown")
                
                # Jika Target OFFLINE
                if status == 0:
                    msg = "🔴 **TARGET OFFLINE!**"
                    send_telegram_msg(msg)
                    current_map = None
                    current_server_id = None

                # Jika Target BERMAIN GAME (Status 2)
                elif status == 2:
                    current_map = new_map
                    current_server_id = new_server_id
                    srv_display = f"\n🆔 **Server ID:** `{new_server_id}`" if new_server_id != "Tidak diketahui" else ""
                    
                    msg = (f"🎮 **TARGET SEDANG BERMAIN!**\n"
                           f"📍 **Map:** `{new_map}`"
                           f"{srv_display}")
                    send_telegram_msg(msg)

                # Jika Target ONLINE biasa (Website / Studio)
                else:
                    msg = f"🚨 **TARGET STATUS BERUBAH!**\nStatus: {status_text}"
                    send_telegram_msg(msg)
                    current_map = None
                    current_server_id = None

                last_status = status
            
    except Exception as e:
        print(f"Error fetch API: {e}")

def run_tracker():
    print("Bot pemantau Roblox aktif...")
    while True:
        check_roblox_status()
        time.sleep(CHECK_INTERVAL)

# Menjalankan pemantau di background thread
threading.Thread(target=run_tracker, daemon=True).start()

# Web Server sederhana untuk syarat Web Service gratis di Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Roblox Simple Tracker Running!")

server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
server.serve_forever()
                
