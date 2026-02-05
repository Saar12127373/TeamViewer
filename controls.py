# client side - Original Structure
import socket
import win32api
import win32con
import keyboard
import ctypes
from threading import Thread
import time
import pyautogui
import struct
from PIL import ImageGrab
import io

# הגדרת מודעות ל-DPI כדי למנוע זיוף במיקום העכבר
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# הגדרות תקשורת
HOST = "192.168.1.129" # שנה ל-IP של השרת שלך
TCP_PORT = 8090
UDP_PORT = 8091

# קבועים לצילום מסך
MAX_UDP_PAYLOAD = 1400
PART_ID_LEN = 3 
MAX_IMAGE_BYTES = MAX_UDP_PAYLOAD - PART_ID_LEN

# ביטול ה-Fail-safe של pyautogui כדי למנוע קריסה בתנועות מהירות
pyautogui.FAILSAFE = False

def recv_all(length, client_sock):
    content = b""
    while(length > 0):
        try:
            tempContent = client_sock.recv(length)
            if not tempContent: return None
            length -= len(tempContent)
            content += tempContent
        except:
            return None
    return content

# --- התחברות לסוקטים ---
keySoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
keySoc.connect((HOST, TCP_PORT))

mouseSoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mouseSoc.connect((HOST, TCP_PORT))

screenSoc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Connected to server!")

# קבלת רזולוציית השרת (חשוב: big endian)
server_width = int.from_bytes(recv_all(2, mouseSoc), "big")
server_heigh = int.from_bytes(recv_all(2, mouseSoc), "big")

def get_screen_resolution():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

client_width, client_heigth = get_screen_resolution()

# --- לוגיקת מקלדת (המבנה המקורי שלך) ---
def key_events():
    while True:
        recieve_event = recv_all(1, keySoc)
        if not recieve_event: break

        # לחיצת מקש
        if recieve_event == b"1":
            recieve_key_type = recv_all(1, keySoc)
            if recieve_key_type == b"1": # תו רגיל
                scan_code = int.from_bytes(recv_all(1, keySoc), "big")
                win32api.keybd_event(scan_code, 0, win32con.KEYEVENTF_EXTENDEDKEY, 0)
            else: # מקש מיוחד
                recieve_key_len = int.from_bytes(recv_all(1, keySoc), "big")
                recieve_key = recv_all(recieve_key_len, keySoc).decode()
                keyboard.press(recieve_key) 

        # שחרור מקש
        elif recieve_event == b"2":
            recieve_key_type = recv_all(1, keySoc)
            if recieve_key_type == b"1": # תו רגיל
                scan_code = int.from_bytes(recv_all(1, keySoc), "big")
                win32api.keybd_event(scan_code, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
            else: # מקש מיוחד
                recieve_key_len = int.from_bytes(recv_all(1, keySoc), "big")
                recieve_key = recv_all(recieve_key_len, keySoc).decode()
                keyboard.release(recieve_key)

# --- לוגיקת עכבר (המבנה המקורי שלך) ---
def mouse_handeling():
    while True:
        mouse_action = recv_all(1, mouseSoc)
        if not mouse_action: break

        if mouse_action == b"0":  # תנועה
            packed_data = recv_all(4, mouseSoc)
            x, y = struct.unpack('hh', packed_data)
            mapped_x = int(x * (client_width / server_width))
            mapped_y = int(y * (client_heigth / server_heigh))
            win32api.SetCursorPos((mapped_x, mapped_y))
    
        elif mouse_action == b"1": # לחיצה (Down)
            button_event = recv_all(1, mouseSoc)
            packed_data = recv_all(4, mouseSoc)
            x, y = struct.unpack('hh', packed_data)
            mapped_x = int(x * (client_width / server_width))
            mapped_y = int(y * (client_heigth / server_heigh))
            
            button = "left" if button_event == b"3" else "right"
            pyautogui.mouseDown(mapped_x, mapped_y, button=button)

        elif mouse_action == b"2": # שחרור (Up)
            button_event = recv_all(1, mouseSoc)
            packed_data = recv_all(4, mouseSoc)
            x, y = struct.unpack('hh', packed_data)
            mapped_x = int(x * (client_width / server_width))
            mapped_y = int(y * (client_heigth / server_heigh))
            
            button = "left" if button_event == b"3" else "right"
            pyautogui.mouseUp(mapped_x, mapped_y, button=button)

# --- לוגיקת צילום מסך ---
def divide_image(image):
    width, height = image.size
    rows, cols = 8, 16
    part_width, part_height = width // cols, height // rows
    parts = []
    for i in range(rows):
        for j in range(cols):
            left, top = j * part_width, i * part_height
            parts.append(image.crop((left, top, left + part_width, top + part_height)))
    return parts

def encode_image_part(part):
    buf = io.BytesIO()
    part.save(buf, format="JPEG", quality=40)
    return buf.getvalue()

def send_screenshot():
    while True:
        try:
            screenshot = ImageGrab.grab()
            image_parts = divide_image(screenshot)
            for idx, part in enumerate(image_parts):
                encoded = encode_image_part(part)
                packet = f"{idx:03}".encode() + encoded
                screenSoc.sendto(packet, (HOST, UDP_PORT))

            screenSoc.sendto(b"1", (HOST, UDP_PORT))
            time.sleep(0.01)
        except:
            break

# --- הפעלה ---
if __name__ == "__main__":
    t1 = Thread(target=key_events)
    t2 = Thread(target=mouse_handeling)
    t3 = Thread(target=send_screenshot)

    t1.start()
    t2.start()        
    t3.start()

    t1.join()
    t2.join()
    t3.join()