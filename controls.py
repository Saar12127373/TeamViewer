import socket
import struct
import time
import ctypes
from threading import Thread
from pynput import mouse
import cv2
import numpy as np

HOST = "0.0.0.0" # Listen on all interfaces
PORT = 8090
UDP_PORT = 8091

# --- NETWORK SETUP ---
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.bind((HOST, PORT))
soc.listen(2)
print(f"Server listening on {HOST}:{PORT}")

# 1. Accept Keyboard Socket
print("Waiting for Keyboard...")
key_sock, addr1 = soc.accept()
key_sock.sendall(b"KEY_OK") # Handshake
print(f"Keyboard connected: {addr1}")

# 2. Accept Mouse Socket
print("Waiting for Mouse...")
mouse_soc, addr2 = soc.accept()
mouse_soc.sendall(b"MOUSE_OK") # Handshake
print(f"Mouse connected: {addr2}")

def recv_all(length, client_sock):
    content = b""
    while length > 0:
        chunk = client_sock.recv(length)
        if not chunk:
            raise ConnectionError("Socket closed")
        length -= len(chunk)
        content += chunk
    return content

def keyTo_scanCode(key):
    try:
        result = ctypes.windll.User32.VkKeyScanW(ord(key))
        return result & 0xFF
    except:
        return 0

def get_screen_resolution():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# Send Resolution
server_w, server_h = get_screen_resolution()
mouse_soc.sendall(int(server_w).to_bytes(2, "big"))
mouse_soc.sendall(int(server_h).to_bytes(2, "big"))

# --- THREADS ---
dwad
def keyBoard_Events():
    import keyboard
    while True:
        try:
            event = keyboard.read_event()
            if event.event_type == "down":
                key_sock.sendall(b"1")
            elif event.event_type == "up":
                key_sock.sendall(b"2")
            
            name = event.name
            if len(name) == 1:
                key_sock.sendall(b"1") # Type: Char
                code = keyTo_scanCode(name)
                key_sock.sendall(int(code).to_bytes(1, "big"))
            else:
                key_sock.sendall(b"2") # Type: Special
                name_bytes = name.encode()
                # Safety: Cap length at 255
                if len(name_bytes) > 255: name_bytes = name_bytes[:255]
                key_sock.sendall(len(name_bytes).to_bytes(1, "big"))
                key_sock.sendall(name_bytes)
        except Exception as e:
            print(f"Key Error: {e}")
            break

def on_move(x, y):
    try:
        mouse_soc.sendall(b"0")
        packed = struct.pack('hh', x, y)
        mouse_soc.sendall(packed)
    except: pass

def on_click(x, y, button, pressed):
    try:
        mouse_soc.sendall(b"1" if pressed else b"2")
        if button == mouse.Button.left: mouse_soc.sendall(b"3")
        elif button == mouse.Button.right: mouse_soc.sendall(b"4")
        else: mouse_soc.sendall(b"5") # Middle/Other
        
        packed = struct.pack('hh', x, y)
        mouse_soc.sendall(packed)
    except: pass

def mouse_managment():
    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        listener.join()

def handle_Screenshots():
    print(f"Opening UDP Stream on port {UDP_PORT}...")
    
    # Retry loop for video connection
    while True:
        # 'udp://@:8091' tells OpenCV to BIND to port 8091
        cap = cv2.VideoCapture(f'udp://@:{UDP_PORT}?overrun_nonfatal=1&fifo_size=500000')
        
        if not cap.isOpened():
            print("Video stream not found, retrying in 2s...")
            time.sleep(2)
            continue

        print("Video Stream Connected!")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Frame dropped / Stream ended")
                break
            
            cv2.imshow('Remote Desktop', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return

# Start
t1 = Thread(target=keyBoard_Events)
t2 = Thread(target=mouse_managment)
t3 = Thread(target=handle_Screenshots)

t1.start()
t2.start()
t3.start()

t1.join()
t2.join()
t3.join()