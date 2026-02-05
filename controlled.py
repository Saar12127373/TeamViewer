import struct
import socket
import ctypes
import time
import io
from threading import Thread
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard
from PIL import Image
import cv2
import numpy as np

# --- הגדרות תקשורת ---
HOST = "0.0.0.0" # מאזין לכל הכתובות
TCP_PORT = 8090
UDP_PORT = 8091

# משתנים גלובליים לניהול Listeners וסגירה
mouse_listener_global = None
running = True

# --- פונקציות עזר ---

def keyTo_scanCode(key):
    """המרת תו ל-Virtual Key Code עבור הלקוח"""
    try:
        result = ctypes.windll.User32.VkKeyScanW(ord(key))
        return result & 0xFF
    except:
        return 0

def send_cords(sock, x, y):
    """שליחת קואורדינטות בפורמט של 4 בייטים (2 לכל ציר)"""
    try:
        packed_data = struct.pack('hh', int(x), int(y))
        sock.sendall(packed_data)
    except:
        pass

# --- ניהול מקלדת ---

def keyBoard_Events(key_sock):
    global running, mouse_listener_global

    def on_press(key):
        global running
        if key == pynput_keyboard.Key.f12:
            print("\n[!] F12 Pressed - Shutting down server...")
            running = False
            if mouse_listener_global:
                mouse_listener_global.stop()
            return False # סוגר את ה-Listener של המקלדת
        
        try:
            if hasattr(key, 'char') and key.char is not None:
                # מקש רגיל
                key_sock.sendall(b"1") # Down
                key_sock.sendall(b"1") # Mode: Char
                scan_code = keyTo_scanCode(key.char)
                key_sock.sendall(int(scan_code).to_bytes(1, "big"))
            else:
                # מקש מיוחד (Alt, Ctrl, וכו')
                name = str(key).replace('Key.', '')
                key_sock.sendall(b"1") # Down
                key_sock.sendall(b"2") # Mode: Special
                key_sock.sendall(len(name).to_bytes(1, "big"))
                key_sock.sendall(name.encode())
        except Exception as e:
            print(f"Key Press Error: {e}")

    def on_release(key):
        if not running: return False
        try:
            if hasattr(key, 'char') and key.char is not None:
                key_sock.sendall(b"2") # Up
                key_sock.sendall(b"1") # Mode: Char
                scan_code = keyTo_scanCode(key.char)
                key_sock.sendall(int(scan_code).to_bytes(1, "big"))
            else:
                name = str(key).replace('Key.', '')
                key_sock.sendall(b"2") # Up
                key_sock.sendall(b"2") # Mode: Special
                key_sock.sendall(len(name).to_bytes(1, "big"))
                key_sock.sendall(name.encode())
        except:
            pass

    with pynput_keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True) as listener:
        listener.join()

# --- ניהול עכבר ---

def mouse_management(mouse_sock):
    global mouse_listener_global, running

    def on_move(x, y):
        if not running: return False
        try:
            mouse_sock.sendall(b"0") # Movement ID
            send_cords(mouse_sock, x, y)
        except: pass

    def on_click(x, y, button, pressed):
        if not running: return False
        try:
            mouse_sock.sendall(b"1" if pressed else b"2") # Click/Release
            btn = b"3" if button == pynput_mouse.Button.left else b"4"
            mouse_sock.sendall(btn)
            send_cords(mouse_sock, x, y)
        except: pass

    mouse_listener_global = pynput_mouse.Listener(on_move=on_move, on_click=on_click, suppress=True)
    with mouse_listener_global as listener:
        listener.join()

# --- ניהול מסך (Video Stream) ---

def receive_screenshot(screen_soc, image_parts):
    while running:
        try:
            data, addr = screen_soc.recvfrom(65535)
            if data == b"1": # סוף פריים
                break
            
            part_index = int(data[:3].decode())
            image_parts[part_index] = data[3:]
        except:
            break

def handle_screenshots(screen_soc):
    cv2.namedWindow('Live Video', cv2.WINDOW_NORMAL)
    while running:
        image_parts = [b""] * 128
        receive_screenshot(screen_soc, image_parts)

        # הרכבת התמונה
        parts = []
        try:
            for p in image_parts:
                if p:
                    parts.append(Image.open(io.BytesIO(p)))
            
            if not parts: continue

            p_width, p_height = parts[0].size
            full_img = Image.new('RGB', (p_width * 16, p_height * 8))

            for i in range(8):
                for j in range(16):
                    idx = i * 16 + j
                    if idx < len(image_parts) and image_parts[idx]:
                        full_img.paste(Image.open(io.BytesIO(image_parts[idx])), (j * p_width, i * p_height))

            cv_img = cv2.cvtColor(np.array(full_img), cv2.COLOR_RGB2BGR)
            cv2.imshow('Live Video', cv_img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except:
            continue
    cv2.destroyAllWindows()

# --- Main ---

if __name__ == "__main__":
    main_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    main_soc.bind((HOST, TCP_PORT))
    main_soc.listen(2)
    print(f"[*] Server started. Listening on {TCP_PORT}...")

    # קבלת חיבורים
    k_sock, _ = main_soc.accept()
    print("[+] Keyboard Socket Connected")
    m_sock, _ = main_soc.accept()
    print("[+] Mouse Socket Connected")

    # שליחת רזולוציה ראשונית (לפי המסך שלך)
    user32 = ctypes.windll.user32
    m_sock.sendall(int(user32.GetSystemMetrics(0)).to_bytes(2, "big"))
    m_sock.sendall(int(user32.GetSystemMetrics(1)).to_bytes(2, "big"))

    screen_soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    screen_soc.bind((HOST, UDP_PORT))

    # הפעלת Threads
    threads = [
        Thread(target=keyBoard_Events, args=(k_sock,)),
        Thread(target=mouse_management, args=(m_sock,)),
        Thread(target=handle_screenshots, args=(screen_soc,))
    ]

    for t in threads: t.start()
    
    # המתנה לסיום (F12)
    threads[0].join() 
    
    # ניקוי
    print("[*] Closing connections...")
    k_sock.close()
    m_sock.close()
    screen_soc.close()
    main_soc.close()
    print("[+] System offline.")