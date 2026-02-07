import socket
import struct
import time
import ctypes
from threading import Thread
from pynput import mouse
import cv2
import numpy as np

HOST = ""
PORT = 8090
UDP_PORT = 8091

# --- NETWORK SETUP (UNCHANGED) ---
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.bind((HOST, PORT))
soc.listen(1)
print("Server is listening!")

key_sock, client_addr1 = soc.accept()
print("Keyboard connected")
mouse_soc, client_addr2 = soc.accept()
print("Mouse connected")

# Note: We no longer need a UDP socket bind for the screen here, 
# because OpenCV will handle the UDP stream connection internally.

# --- INPUT LOGIC (UNCHANGED) ---

def recv_all(length, client_sock):
    content = b""
    while(length > 0):
        tempContent = client_sock.recv(length)
        length -= len(tempContent)
        content += tempContent
    return content

def keyTo_scanCode(key):
    result = ctypes.windll.User32.VkKeyScanW(ord(key))
    vk_key = result & 0xFF
    return vk_key

def get_screen_resolution():
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    return screen_width, screen_height

server_width, server_heigth = get_screen_resolution()
print(f"Server Resolution: {server_width}x{server_heigth}")

mouse_soc.sendall(int(server_width).to_bytes(2, "big"))
mouse_soc.sendall(int(server_heigth).to_bytes(2, "big"))

def keyBoard_Events():
    import keyboard # Import locally to avoid issues if not used in main scope
    while True:
        event = keyboard.read_event()
        event_type = event.event_type
        event_name = event.name

        if event_type == "down":
            key_sock.sendall(b"1")
        elif event_type == "up":
            key_sock.sendall(b"2")
        
        if len(event_name) == 1:
            key_sock.sendall(b"1")
            scan_code = keyTo_scanCode(event_name)
            key_sock.sendall(int(scan_code).to_bytes(1, "big"))
        else:
            key_sock.sendall(b"2")
            key_sock.sendall(len(event_name).to_bytes(1, "big"))
            key_sock.sendall(event_name.encode())

def on_move(x, y):
    mouse_soc.sendall(b"0")
    send_cords(x, y)

def on_click(x, y, button, pressed):
    if pressed:
        mouse_soc.sendall(b"1")
    else:
        mouse_soc.sendall(b"2")

    if button == mouse.Button.left:
        mouse_soc.sendall(b"3")
    elif button == mouse.Button.right:
        mouse_soc.sendall(b"4")
    
    send_cords(x, y)

def send_cords(x,y):
    packed_data = struct.pack('hh', x, y)
    mouse_soc.sendall(packed_data)
    # print(x,y) # Commented out to reduce spam
    time.sleep(0.01)

def mouse_managment():
    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        listener.join()

# --- NEW SCREEN LOGIC (FFMPEG LISTENER) ---

def handle_Screenshots():
    print("Waiting for video stream...")
    # Listen on UDP port 8091. 
    # 'mpegts' is the container format we will send from the client.
    cap = cv2.VideoCapture(f'udp://@:{UDP_PORT}?overrun_nonfatal=1&fifo_size=50000000')

    if not cap.isOpened():
        print("Error: Could not open video stream.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            # If no frame is received, just wait a bit and try again
            time.sleep(0.01)
            continue

        cv2.imshow('Remote Desktop (FFmpeg)', frame)
        
        # Press 'q' to exit the video window (optional)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

# --- EXECUTION ---

keyboard_thread = Thread(target=keyBoard_Events)
mouse_thread = Thread(target=mouse_managment)
screen_thread = Thread(target=handle_Screenshots)

keyboard_thread.start()
mouse_thread.start()
screen_thread.start()

keyboard_thread.join()
mouse_thread.join()
screen_thread.join()

key_sock.close()
mouse_soc.close()
soc.close()