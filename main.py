import os, time, base64, json, re, hashlib, requests
from datetime import datetime

BOOKING_URL = os.getenv("BOOKING_URL", "").strip()
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "60"))
COOKIES_B64 = os.getenv("COOKIES_B64", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def ts(): 
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_tg(text):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID): 
        print(f"[{ts()}] (ingen Telegram config)")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True}, timeout=20)
        r.raise_for_status()
        print(f"[{ts()}] Telegram skickat.")
    except Exception as e:
        print(f"[{ts()}] Telegram fel: {e}")

def load_session():
    s = requests.Session()
    if COOKIES_B64:
        try:
            data = base64.b64decode(COOKIES_B64).decode("utf-8", "ignore")
            cookies = json.loads(data)
            for c in cookies:
                name = c.get("name"); value = c.get("value")
                domain = c.get("domain")
                path = c.get("path") or "/"
                if name is None or value is None: 
                    continue
                s.cookies.set(name, value, domain=domain, path=path)
            print(f"[{ts()}] Lade in {len(cookies)} cookies.")
        except Exception as e:
            print(f"[{ts()}] Cookies fel: {e}")
    return s

def extract_times(text):
    # hittar klockslag som 08:15, 13:20 osv
    return sorted(set(re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", text)))

def sha1(s):
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()

def main():
    if not BOOKING_URL:
        print("Sätt BOOKING_URL i Environment Variables.")
        return

    print(f"[{ts()}] Startar bevakning")
    print(f"URL: {BOOKING_URL}")
    print(f"Intervall: {POLL_INTERVAL_SEC}s")

    s = load_session()
    last_hash = ""
    last_times = []

    # Skicka “igång” ping
    send_tg("🚦 Trafikvakten är igång.")

    while True:
        try:
            r = s.get(BOOKING_URL, timeout=60)
            if r.status_code >= 400:
                print(f"[{ts()}] HTTP {r.status_code} – kan kräva nya cookies.")
            html = r.text
            cur_hash = sha1(html)
            times = extract_times(html)

            if cur_hash != last_hash:
                msg = "Sidan ändrades"
                if times:
                    msg += f" – tider: {', '.join(times)}"
                msg += f"\n{BOOKING_URL}"
                print(f"[{ts()}] Förändring upptäckt → skickar notis.")
                send_tg(msg)
                last_hash = cur_hash
                last_times = times
            else:
                if times and times != last_times:
                    new_only = sorted(set(times) - set(last_times))
                    if new_only:
                        send_tg(f"Nya tider: {', '.join(new_only)}\n{BOOKING_URL}")
                        last_times = times
                else:
                    print(f"[{ts()}] Ingen förändring.")
        except Exception as e:
            print(f"[{ts()}] Fel: {e}")
        time.sleep(POLL_INTERVAL_SEC)

if __name__ == "__main__":
    main()
