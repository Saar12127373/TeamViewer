import socket
import ctypes
import struct
import subprocess
import os
import keyboard  # וודא שמותקן: pip install keyboard
from threading import Thread
from pynput import mouse

HOST = "0.0.0.0"
PORT = 8090
FFPLAY_PORT = 9000

# הגדרות FFplay
def run_ffplay():
    url = f"srt://:{FFPLAY_PORT}?mode=listener&latency=80"
    cmd = [
        "ffplay", "-fs", "-noborder", "-hide_banner", "-loglevel", "warning",
        "-fflags", "nobuffer", "-flags", "low_delay", "-framedrop", "-sync", "ext", url
    ]
    return subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)

# לוגיקת המקלדת
def keyTo_scanCode(key):
    try:
        result = ctypes.windll.User32.VkKeyScanW(ord(key))
        return result & 0xFF
    except: return 0

def keyboard_events():
    while True:
        event = keyboard.read_event()
        # שליחת סוג האירוע: 1 ללחיצה, 2 לשחרור
        key_sock.sendall(b"1" if event.event_type == "down" else b"2")
        
        if len(event.name) == 1: # תו רגיל
            key_sock.sendall(b"1")
            scan_code = keyTo_scanCode(event.name)
            key_sock.sendall(int(scan_code).to_bytes(1, "big"))
        else: # מקש מיוחד (Enter, Alt...)
            key_sock.sendall(b"2")
            name_bytes = event.name.encode()
            key_sock.sendall(len(name_bytes).to_bytes(1, "big"))
            key_sock.sendall(name_bytes)

# הקמת שקעים
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.bind((HOST, PORT))
soc.listen(2)
print("Waiting for connections...")

key_sock, _ = soc.accept()
mouse_soc, _ = soc.accept()

# שליחת רזולוציה
user32 = ctypes.windll.user32
sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
mouse_soc.sendall(sw.to_bytes(2, "big"))
mouse_soc.sendall(sh.to_bytes(2, "big"))

# הפעלה
ffplay_proc = run_ffplay()
Thread(target=keyboard_events, daemon=True).start()

# לוגיקת עכבר (on_move, on_click) - כפי שהופיעה קודם
def on_move(x, y):
    try:
        mouse_soc.sendall(b"0")
        mouse_soc.sendall(struct.pack('hh', x, y))
    except: pass

with mouse.Listener(on_move=on_move) as listener:
    listener.join()