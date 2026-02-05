import socket
import win32api
import win32con
import keyboard
import ctypes
from threading import Thread
import time
import struct
from PIL import ImageGrab
import io

# הגדרת DPI כדי שהעכבר יהיה מדויק גם במסכים עם Scaling
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except: pass

HOST = "192.168.1.129" # וודא שזו הכתובת של השרת
TCP_PORT = 8090
UDP_PORT = 8091

MAX_UDP_PAYLOAD = 1400
PART_ID_LEN = 3 
MAX_IMAGE_BYTES = MAX_UDP_PAYLOAD - PART_ID_LEN

def recv_all(length, client_sock):
    content = b""
    while length > 0:
        try:
            temp = client_sock.recv(length)
            if not temp: return None
            length -= len(temp)
            content += temp
        except: return None
    return content

# --- התחברות ---
keySoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
keySoc.connect((HOST, TCP_PORT))

mouseSoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mouseSoc.connect((HOST, TCP_PORT))

screenSoc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("Connected to Server!")

# קבלת רזולוציית השרת
server_width = int.from_bytes(recv_all(2, mouseSoc), "big")
server_height = int.from_bytes(recv_all(2, mouseSoc), "big")

def get_screen_res():
    u32 = ctypes.windll.user32
    return u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)

client_w, client_h = get_screen_res()

# --- ניהול מקלדת ---
def key_events():
    translation = {
        'alt_l': 'alt', 'alt_r': 'alt gr',
        'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
        'shift_l': 'shift', 'shift_r': 'shift',
        'cmd': 'windows', 'caps_lock': 'caps lock',
        'enter': 'enter', 'esc': 'esc', 'space': 'space'
    }
    while True:
        event_type = recv_all(1, keySoc) # 1=Down, 2=Up
        if not event_type: break
        key_mode = recv_all(1, keySoc)   # 1=Char, 2=Special

        if key_mode == b"1":
            scan_code = int.from_bytes(recv_all(1, keySoc), "big")
            flag = 0 if event_type == b"1" else win32con.KEYEVENTF_KEYUP
            win32api.keybd_event(scan_code, 0, win32con.KEYEVENTF_EXTENDEDKEY | flag, 0)
        else:
            name_len = int.from_bytes(recv_all(1, keySoc), "big")
            name = recv_all(name_len, keySoc).decode()
            final_name = translation.get(name, name)
            if event_type == b"1": keyboard.press(final_name)
            else: keyboard.release(final_name)

# --- ניהול עכבר ---
def mouse_handeling():
    while True:
        action = recv_all(1, mouseSoc)
        if not action: break

        if action == b"0": # Move
            data = recv_all(4, mouseSoc)
            sx, sy = struct.unpack('hh', data)
            win32api.SetCursorPos((int(sx * client_w/server_width), int(sy * client_h/server_height)))
        
        elif action in [b"1", b"2"]: # Click/Release
            is_down = (action == b"1")
            btn = recv_all(1, mouseSoc)
            data = recv_all(4, mouseSoc)
            sx, sy = struct.unpack('hh', data)
            
            win32api.SetCursorPos((int(sx * client_w/server_width), int(sy * client_h/server_height)))
            
            if btn == b"3": # Left
                flag = win32con.MOUSEEVENTF_LEFTDOWN if is_down else win32con.MOUSEEVENTF_LEFTUP
            else: # Right
                flag = win32con.MOUSEEVENTF_RIGHTDOWN if is_down else win32con.MOUSEEVENTF_RIGHTUP
            win32api.mouse_event(flag, 0, 0, 0, 0)

# --- ניהול מסך ---
def divide_image(image):
    rows, cols = 8, 16
    pw, ph = image.width // cols, image.height // rows
    return [image.crop((j*pw, i*ph, (j+1)*pw, (i+1)*ph)) for i in range(rows) for j in range(cols)]

def encode_image_part(part):
    buf = io.BytesIO()
    part.save(buf, format="JPEG", quality=40)
    return buf.getvalue()

def send_screenshot():
    while True:
        try:
            screenshot = ImageGrab.grab()
            parts = divide_image(screenshot)
            for idx, part in enumerate(parts):
                encoded = encode_image_part(part)
                packet = f"{idx:03}".encode() + encoded
                screenSoc.sendto(packet, (HOST, UDP_PORT))
            screenSoc.sendto(b"1", (HOST, UDP_PORT))
            time.sleep(0.02)
        except: break

if __name__ == "__main__":
    t1 = Thread(target=key_events, daemon=True)
    t2 = Thread(target=mouse_handeling, daemon=True)
    t3 = Thread(target=send_screenshot, daemon=True)
    
    for t in [t1, t2, t3]: t.start()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass