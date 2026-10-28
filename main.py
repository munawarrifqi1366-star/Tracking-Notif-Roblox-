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
current_server_id = None
map_start_time = None
map_history = []  # Menyimpan daftar riwayat map, server ID, dan durasi

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
    global last_status, current_map, current_server_id, map_start_time, map_history
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [ROBLOX_USER_ID]}
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if "userPresences" in data and len(data["userPresences"]) > 0:
            user_data = data["userPresences"][0]
            status = user_data.get("userPresenceType", 0)
            
            # Ambil informasi lokasi/map dan gameId (Server ID) jika sedang bermain (status 2)
            new_map = "Tidak diketahui"
            new_server_id = "Tidak diketahui"
            
            if status == 2:
                if "lastLocation" in user_data and user_data["lastLocation"]:
                    new_map = user_data["lastLocation"]
                else:
                    new_map = "Bermain Game (Nama Map Privat/Hidden)"
                
                # Mengambil gameId sebagai ID Server unik dari Roblox
                if "gameId" in user_data and user_data["gameId"]:
                    new_server_id = user_data["gameId"]

            now = time.time()

            # Deteksi Perubahan Status, Map, atau Server ID
            is_map_or_server_changed = (status == 2 and (new_map != current_map or new_server_id != current_server_id))
            
            if last_status is not None and (status != last_status or is_map_or_server_changed):
                
                # Jika sebelumnya sedang di map/server tertentu, hitung durasinya sebelum pindah/offline
                if last_status == 2 and current_map is not None:
                    duration_sec = int(now - map_start_time)
                    duration_str = format_duration(duration_sec)
                    map_history.append({
                        "map": current_map,
                        "server_id": current_server_id,
                        "duration": duration_str
                    })

                # Jika player beralih ke OFFLINE (Status 0)
                if status == 0:
                    status_text = STATUS_MAP.get(status, "Offline")
                    
                    # Buat rekap riwayat map & server
                    history_summary = ""
                    if map_history:
                        history_summary = "\n\n🗺️ **Riwayat Perjalanan Map & Server:**\n"
                        for idx, item in enumerate(map_history, 1):
                            srv_display = f" (ID: `{item['server_id']}`)" if item['server_id'] != "Tidak diketahui" else ""
                            history_summary += f"{idx}. {item['map']}{srv_display}\n   ⏱️ Durasi: {item['duration']}\n"
                    
                    msg = f"🔴 **TARGET OFFLINE!**{history_summary}"
                    send_telegram_msg(msg)
                    
                    # Reset data setelah offline
                    current_map = None
                    current_server_id = None
                    map_start_time = None
                    map_history = []

                # Jika player ONLINE / BERMAIN / PINDAH MAP / PINDAH SERVER
                else:
                    status_text = STATUS_MAP.get(status, "Unknown")
                    
                    # Jika sedang bermain (status 2)
                    if status == 2:
                        current_map = new_map
                        current_server_id = new_server_id
                        map_start_time = now
                        
                        # Format tampilan ID server
                        server_display = f" (ID: `{new_server_id}`)" if new_server_id != "Tidak diketahui" else ""
                        
                        # Susun pesan perpindahan
                        msg = (f"🚨 **TARGET UPDATE STATUS!**\n"
                               f"Status: {status_text}\n"
                               f"📍 Masuk ke Map: `{new_map}`{server_display}")
                        send_telegram_msg(msg)
                    else:
                        # Status online biasa (website/studio)
                        current_map = None
                        current_server_id = None
                        map_start_time = None
                        msg = f"🚨 **TARGET STATUS BERUBAH!**\nStatus: {status_text}"
                        send_telegram_msg(msg)

            # Inisialisasi awal jika bot baru menyala dan user sudah dalam kondisi bermain
            elif last_status is None and status == 2:
                current_map = new_map
                current_server_id = new_server_id
                map_start_time = now

            last_status = status
            
    exceptException as e:
        print(f"Error fetch API: {e}")

def run_tracker():
    print("Bot pemantau Roblox dengan pelacakan map & server ID aktif...")
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
        self.wfile.write(b"Roblox Map & Server Tracker Running!")

server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
server.serve_forever()
