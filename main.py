import requests
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# --- KONFIGURASI ---
TELEGRAM_BOT_TOKEN = "7955453002:AAFvmfj9oWPaVfm1weNz1C1m-dzbxwioEJs"
TELEGRAM_CHAT_ID = "7376896906"
ROBLOX_USER_ID = 9465641652  # User ID target
CHECK_INTERVAL = 15  # Cek setiap 15 detik

STATUS_MAP = {
    0: "Offline",
    1: "Online di Website",
    2: "Sedang Bermain Game 🎮",
    3: "Sedang di Roblox Studio 🛠️"
}

last_status = None
current_map = None
map_start_time = None
map_history = []  # Menyimpan daftar riwayat map dan durasi

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error kirim pesan: {e}")

def format_duration(seconds):
    """Mengubah detik menjadi format jam:menit:detik"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours} jam {minutes} menit {secs} detik"
    elif minutes > 0:
        return f"{minutes} menit {secs} detik"
    else:
        return f"{secs} detik"

def check_roblox_status():
    global last_status, current_map, map_start_time, map_history
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [ROBLOX_USER_ID]}
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if "userPresences" in data and len(data["userPresences"]) > 0:
            user_data = data["userPresences"][0]
            status = user_data.get("userPresenceType", 0)
            
            # Ambil informasi lokasi/map jika sedang bermain (status 2)
            new_map = "Tidak diketahui"
            if status == 2 and "lastLocation" in user_data:
                new_map = user_data["lastLocation"]
                if not new_map: # Jika lastLocation kosong
                    new_map = "Bermain Game (Nama Map Privat/Hidden)"

            now = time.time()

            # Deteksi Perubahan Status atau Map
            if last_status is not None and (status != last_status or (status == 2 and new_map != current_map)):
                
                # Jika sebelumnya sedang di map tertentu, hitung durasinya sebelum pindah/offline
                if last_status == 2 and current_map is not None:
                    duration_sec = int(now - map_start_time)
                    duration_str = format_duration(duration_sec)
                    map_history.append({
                        "map": current_map,
                        "duration": duration_str
                    })

                # Jika player beralih ke OFFLINE (Status 0)
                if status == 0:
                    status_text = STATUS_MAP.get(status, "Offline")
                    
                    # Buat rekap riwayat map
                    history_summary = ""
                    if map_history:
                        history_summary = "\n\n🗺️ **Riwayat Perjalanan Map:**\n"
                        for idx, item in enumerate(map_history, 1):
                            history_summary += f"{idx}. {item['map']} (Durasi: {item['duration']})\n"
                    
                    msg = f"🔴 **TARGET OFFLINE!**{history_summary}"
                    send_telegram_msg(msg)
                    
                    # Reset data setelah offline
                    current_map = None
                    map_start_time = None
                    map_history = []

                # Jika player ONLINE / BERMAIN / PINDAH MAP
                else:
                    status_text = STATUS_MAP.get(status, "Unknown")
                    
                    # Jika pindah map atau baru masuk game
                    if status == 2:
                        current_map = new_map
                        map_start_time = now
                        
                        # Susun pesan perpindahan
                        msg = (f"🚨 **TARGET UPDATE STATUS!**\n"
                               f"Status: {status_text}\n"
                               f"📍 Masuk ke Map: `{new_map}`")
                        send_telegram_msg(msg)
                    else:
                        # Status online biasa (website/studio)
                        current_map = None
                        map_start_time = None
                        msg = f"🚨 **TARGET STATUS BERUBAH!**\nStatus: {status_text}"
                        send_telegram_msg(msg)

            # Inisialisasi awal jika bot baru menyala dan user sudah dalam kondisi bermain
            elif last_status is None and status == 2:
                current_map = new_map
                map_start_time = now

            last_status = status
            
    except Exception as e:
        print(f"Error fetch API: {e}")

def run_tracker():
    print("Bot pemantau Roblox dengan pelacakan map aktif...")
    while True:
        check_roblox_status()
        time.sleep(CHECK_INTERVAL)

# Menjalankan pemantau di background thread
threading.Thread(target=run_tracker, daemon=True).start()

# Fake Web Server untuk syarat Web Service gratis di Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Roblox Map Tracker Running!")

server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
server.serve_forever()
