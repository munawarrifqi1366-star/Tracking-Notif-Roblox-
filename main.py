import requests
import time

# --- KONFIGURASI ---
TELEGRAM_BOT_TOKEN = "7955453002:AAFvmfj9oWPaVfm1weNz1C1m-dzbxwioEJs"
TELEGRAM_CHAT_ID = "7376896906"
ROBLOX_USER_ID = 9465641652  # Ganti dengan User ID target
CHECK_INTERVAL = 60  # Cek setiap 60 detik

# Mapping status Roblox
STATUS_MAP = {
    0: "Offline",
    1: "Online di Website",
    2: "Sedang Bermain Game 🎮",
    3: "Sedang di Roblox Studio 🛠️"
}

last_status = None

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error kirim pesan: {e}")

def check_roblox_status():
    global last_status
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [ROBLOX_USER_ID]}
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        if "userPresences" in data and len(data["userPresences"]) > 0:
            user_data = data["userPresences"][0]
            current_status = user_data.get("userPresenceType", 0)
            
            # Jika status berubah dari sebelumnya
            if last_status is not None and current_status != last_status:
                status_text = STATUS_MAP.get(current_status, "Unknown")
                
                # Kirim notifikasi hanya jika berubah jadi Online/In-Game
                if current_status in [1, 2]:
                    game_info = ""
                    if current_status == 2 and "lastLocation" in user_data:
                        game_info = f"\nGame: {user_data['lastLocation']}"
                    
                    msg = f"🚨 **TARGET ONLINE ROBLOX!**\nStatus: {status_text}{game_info}"
                    send_telegram_msg(msg)
                elif current_status == 0:
                    send_telegram_msg("🔴 Target baru saja Offline.")

            last_status = current_status
    except Exception as e:
        print(f"Error fetch API: {e}")

print("Bot pemantau Roblox aktif...")
while True:
    check_roblox_status()
    time.sleep(CHECK_INTERVAL)
