import os
import json
import time
import urllib.request
import urllib.error

WALLPAPER_FILE = None

def init_app(app):
    global WALLPAPER_FILE
    WALLPAPER_FILE = os.path.join(app.instance_path, "wallpaper.json")
    os.makedirs(os.path.dirname(WALLPAPER_FILE), exist_ok=True)

def get_wallpaper():
    if not WALLPAPER_FILE or not os.path.isfile(WALLPAPER_FILE):
        return ""
    try:
        with open(WALLPAPER_FILE, "r") as f:
            data = json.load(f)
        return data.get("url", "")
    except:
        return ""

def fetch_new():
    url = "https://cdn.8845.top/api/limo?orientation=pc"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            final_url = resp.geturl()
        if final_url:
            save(final_url)
            return final_url
    except Exception:
        pass
    return ""

def save(url):
    if not WALLPAPER_FILE:
        return
    with open(WALLPAPER_FILE, "w") as f:
        json.dump({"url": url, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)

def clear():
    if WALLPAPER_FILE and os.path.isfile(WALLPAPER_FILE):
        os.remove(WALLPAPER_FILE)
