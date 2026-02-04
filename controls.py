# server side:


import struct
import socket
import keyboard 
import ctypes
import time
from threading import Thread
from pynput import mouse
from PIL import Image
import io
import cv2
import numpy as np








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
    




# this kind of way isnt possible, the only way i found out possible is to know where to click in the keyboard

# def keyDown(event):
    # Sending choice for key down
    # client_sock.sendall(b"1")

    # # vk = 0
    # key=0
    # try:
    #     key = event.name
    #     sliced = key.find("_")
    #     if sliced != -1:
    #         key = key[:sliced]
    #     # vk = event.value.vk
    # except:
    #     key = event.char
    #     # vk = event.vk
    # client_sock.sendall(len(key).to_bytes(1, "big"))
    # print(f"Key down: {key}")
    # client_sock.sendall(key.encode())


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
    while True:
        event = keyboard.read_event()
        event_type = event.event_type
        event_name = event.name

        # key pressed
        if event_type == "down":
            key_sock.sendall(b"1")
        # key released
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
    mouse_soc.sendall(b"0")  # Indicate a movement event
    send_cords(x, y)


def on_click(x, y, button, pressed):
    if pressed:
        mouse_soc.sendall(b"1")  # Indicate a click event
    else:
        mouse_soc.sendall(b"2")  # Indicate a release event

    # Send button type 
    if button == mouse.Button.left:
        mouse_soc.sendall(b"3")  # Left button
    elif button == mouse.Button.right:
        mouse_soc.sendall(b"4")  # Right button
    
    send_cords(x, y)


def send_cords(x,y):
        # placment will always be between 1 -2 bytes so not worth sending length
        #sending cords, also being able to send negative
        packed_data = struct.pack('hh', x, y)
        mouse_soc.sendall(packed_data)
        time.sleep(0.01)



def mouse_managment():

    with mouse.Listener(on_move = on_move, on_click=on_click) as listener:
        listener.join()


# Initialize with black image parts
# def initialize_image_parts(part_width, part_height):
#     black_part = Image.new('RGB', (part_width, part_height), (0, 0, 0))
#     black_part_data = io.BytesIO()
#     black_part.save(black_part_data, format='JPEG')
#     black_part_bytes = black_part_data.getvalue()
    
#     return [black_part_bytes] * 128

# added now
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



# def load_screenshot(image_parts):
#     parts = [Image.open(io.BytesIO(part)) for part in image_parts]

#     # Ensure the width and height calculations match image layout
#     part_width, part_height = parts[0].size
#     width, height = part_width * 16, part_height * 8

#     full_image = Image.new('RGB', (width, height))

#     for i in range(8):
#         for j in range(16):
#             full_image.paste(parts[i * 16 + j], (j * part_width, i * part_height))

#     cv_image = np.array(full_image)
#     cv_image = cv_image[:, :, ::-1]  # from RGB to BGR
#     cv2.imshow('Live Video', cv_image)
#     cv2.waitKey(4)

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







# def handle_Screenshots():
#     part_width, part_height = 1920 // 16, 1080 // 8  # Adjust based on image part sizes
#     while True:
 
#         image_parts = initialize_image_parts(part_width, part_height)

#         # Receive screenshots
#         receive_screenshot(image_parts)

#         # Process and display the received screenshot
#         load_screenshot(image_parts)
    
# added now

def make_black_part_bytes(part_width, part_height):
    black_part = Image.new('RGB', (part_width, part_height), (0, 0, 0))
    buf = io.BytesIO()
    black_part.save(buf, format='JPEG', quality=30, optimize=True)
    return buf.getvalue()

# def handle_Screenshots():
#     rows, cols = 8, 16

#     screen_w, screen_h = get_screen_resolution()
#     part_width = screen_w // cols
#     part_height = screen_h // rows
#     while True:
#         image_parts, default_part_bytes = initialize_image_parts(part_width, part_height)

#         receive_screenshot(image_parts)

#         load_screenshot(image_parts, default_part_bytes)

#changed
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