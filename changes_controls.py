# server side:


import struct
import socket
import ctypes
import time
from threading import Thread
from pynput import mouse
from PIL import Image
import io
import cv2
import numpy as np

from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse








HOST = ""
PORT = 8090
UDP_PORT = 8091


# creating socket, specifing ipv4 and tcp
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# as a tuple giving ip and port
soc.bind((HOST, PORT))
    # waiting for connection
soc.listen(1)
print("Server is listening!")

# key, mouse, screen socks are  new socket objects for send and recv msg
# client addr is the ip and port 
        
key_sock, client_addr1 = soc.accept()
    
mouse_soc, client_addr2 = soc.accept()

# Create UDP socket for screenshots
screen_soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
screen_soc.bind((HOST, UDP_PORT))



# recover all data sent                          
def recv_all(length, client_sock):
    content = b""
    while(length > 0):
        tempContent = client_sock.recv(length)
        length -= len(tempContent)
        content += tempContent
    return content

 # geting the key code (only if not a speacial letter)
def keyTo_scanCode(key):
    result = ctypes.windll.User32.VkKeyScanW(ord(key))
    vk_key = result & 0xFF
    return vk_key
    


def get_screen_resolution():
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    return screen_width, screen_height

server_width, server_heigth = get_screen_resolution()
print(server_width, server_heigth)

mouse_soc.sendall(int(server_width).to_bytes(2, "big"))
mouse_soc.sendall(int(server_heigth).to_bytes(2, "big"))

def keyBoard_Events():
    global running
    def on_press(key):
        global running
        if key == pynput_keyboard.Key.f12:
            running = False
            if mouse_listener_global: mouse_listener_global.stop()
            return False 
        try:
            if hasattr(key, 'char') and key.char is not None:
                key_sock.sendall(b"1") # Event: Down
                key_sock.sendall(b"1") # Mode: Char
                scan_code = keyTo_scanCode(key.char)
                key_sock.sendall(int(scan_code).to_bytes(1, "big"))
            else:
                name = str(key).replace('Key.', '')
                key_sock.sendall(b"1") # Event: Down
                key_sock.sendall(b"2") # Mode: Special
                key_sock.sendall(len(name).to_bytes(1, "big"))
                key_sock.sendall(name.encode())
        except: pass

    def on_release(key):
        if key == pynput_keyboard.Key.f12: return False
        try:
            if hasattr(key, 'char') and key.char is not None:
                key_sock.sendall(b"2") # Event: Up
                key_sock.sendall(b"1") # Mode: Char
                scan_code = keyTo_scanCode(key.char)
                key_sock.sendall(int(scan_code).to_bytes(1, "big"))
            else:
                name = str(key).replace('Key.', '')
                key_sock.sendall(b"2") # Event: Up
                key_sock.sendall(b"2") # Mode: Special
                key_sock.sendall(len(name).to_bytes(1, "big"))
                key_sock.sendall(name.encode())
        except: pass

    with pynput_keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True) as listener:
        listener.join()

# def on_move(x, y):
#     mouse_soc.sendall(b"0")  # Indicate a movement event
#     send_cords(x, y)


# def on_click(x, y, button, pressed):
#     if pressed:
#         mouse_soc.sendall(b"1")  # Indicate a click event
#     else:
#         mouse_soc.sendall(b"2")  # Indicate a release event

#     # Send button type 
#     if button == mouse.Button.left:
#         mouse_soc.sendall(b"3")  # Left button
#     elif button == mouse.Button.right:
#         mouse_soc.sendall(b"4")  # Right button
    
#     send_cords(x, y)



# def mouse_managment():

#     with mouse.Listener(on_move = on_move, on_click=on_click) as listener:
#         listener.join()

# --- MOUSE WITH SUPPRESS ---

def mouse_managment():
    def on_move(x, y):
        mouse_soc.sendall(b"0")
        send_cords(x, y)

    def on_click(x, y, button, pressed):
        mouse_soc.sendall(b"1" if pressed else b"2")
        btn = b"3" if button == pynput_mouse.Button.left else b"4"
        mouse_soc.sendall(btn)
        send_cords(x, y)

    with pynput_mouse.Listener(on_move=on_move, on_click=on_click, suppress=True) as listener:
        listener.join()

def send_cords(x,y):
        # placment will always be between 1 -2 bytes so not worth sending length
        #sending cords, also being able to send negative
        packed_data = struct.pack('hh', x, y)
        mouse_soc.sendall(packed_data)
        time.sleep(0.01)

def send_cords(x,y):
    # placment will always be between 1 -2 bytes so not worth sending length
    #sending cords, also being able to send negative
    packed_data = struct.pack('hh', int(x), int(y))
    mouse_soc.sendall(packed_data)
    time.sleep(0.01)



def initialize_image_parts(part_width, part_height):
    black_part = Image.new('RGB', (part_width, part_height), (0, 0, 0))
    black_part_data = io.BytesIO()
    black_part.save(black_part_data, format='JPEG', quality=30, optimize=True)
    black_part_bytes = black_part_data.getvalue()

    image_parts = [black_part_bytes] * 128
    return image_parts, black_part_bytes

def receive_screenshot(image_parts):
    # i took down the part of checking the orded of the packets - the reason is: the deiffrence between the speed

    while True:
        data, addr = screen_soc.recvfrom(65535)
        if(data == b"1"):
            break

        part_id_len = 3

        part_id = data[:part_id_len].decode()
        part_data = data[part_id_len:]
        
        # integer will ignore 0
        part_index = int(part_id)
        image_parts[part_index] = part_data



#added now
def load_screenshot(image_parts, default_part_bytes):
    parts = []
    for part in image_parts:
        try:
            img = Image.open(io.BytesIO(part))
            parts.append(img)
        except:
            img = Image.open(io.BytesIO(default_part_bytes))
            parts.append(img)

    part_width, part_height = parts[0].size
    width, height = part_width * 16, part_height * 8

    full_image = Image.new('RGB', (width, height))

    for i in range(8):
        for j in range(16):
            full_image.paste(parts[i * 16 + j], (j * part_width, i * part_height))

    cv_image = np.array(full_image)
    cv_image = cv_image[:, :, ::-1]
    cv2.imshow('Live Video', cv_image)
    cv2.waitKey(1)








def make_black_part_bytes(part_width, part_height):
    black_part = Image.new('RGB', (part_width, part_height), (0, 0, 0))
    buf = io.BytesIO()
    black_part.save(buf, format='JPEG', quality=30, optimize=True)
    return buf.getvalue()


def handle_Screenshots():
    cv2.namedWindow('Live Video', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Live Video', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    while True:
        # זמני: נכין רשימה ריקה (או עם bytes ריקים)
        image_parts = [b""] * 128

        receive_screenshot(image_parts)

        # נשתמש בגודל אמיתי מהחלק הראשון שהגיע
        first_part_bytes = None
        for p in image_parts:
            if p:
                first_part_bytes = p
                break

        if first_part_bytes is None:
            continue  # לא הגיע שום חלק בפריים הזה

        first = Image.open(io.BytesIO(first_part_bytes))
        part_width, part_height = first.size

        default_part_bytes = make_black_part_bytes(part_width, part_height)

        # מלא חסרים ב-default (רק אם ריק)
        for i in range(128):
            if not image_parts[i]:
                image_parts[i] = default_part_bytes

        load_screenshot(image_parts, default_part_bytes)



# Create threads for each function so they both will work at the same time:

keyboard_thread = Thread(target=keyBoard_Events)
mouse_thread = Thread(target=mouse_managment)
screen_thread = Thread(target=handle_Screenshots)

keyboard_thread.start()
mouse_thread.start()
screen_thread.start()


keyboard_thread.join()
mouse_thread.join()
screen_thread.join()


#closing sockets:
key_sock.close()
mouse_soc.close()
screen_soc.close()

soc.close()


# thers an explanation about the program in a file named explanation.txt