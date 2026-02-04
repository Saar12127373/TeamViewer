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



try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass




HOST = "192.168.1.127"
TCP_PORT = 8090
UDP_PORT = 8091


#constants
MAX_UDP_PAYLOAD = 1400
PART_ID_LEN = 3  # "000"
MAX_IMAGE_BYTES = MAX_UDP_PAYLOAD - PART_ID_LEN



def recv_all(length, client_sock):
    content = b""
    while(length > 0):
        tempContent = client_sock.recv(length)
        length -= len(tempContent)
        content += tempContent
    return content




keySoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
keySoc.connect((HOST, TCP_PORT))


mouseSoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mouseSoc.connect((HOST, TCP_PORT))

screenSoc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


print("server connectes! ")



server_width = int.from_bytes(recv_all(2, mouseSoc), "big")
server_heigh = int.from_bytes(recv_all(2, mouseSoc), "big")

def get_screen_resolution():
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)  
    screen_height = user32.GetSystemMetrics(1)  
    return screen_width, screen_height

client_width, client_heigth = get_screen_resolution()


def key_events():
    while True:
        # Receive choice
        recieve_event = recv_all(1, keySoc)


        # keyboard press:
        if recieve_event == b"1":
            recieve_key_type = recv_all(1, keySoc)

            # not speacial char
            if(recieve_key_type == b"1"):
                    
                # Receive key press
                scan_code = int.from_bytes(recv_all(1, keySoc), "big")
                win32api.keybd_event(scan_code, 0, win32con.KEYEVENTF_EXTENDEDKEY, 0)

            
            # special letter
            else:

                recieve_key_len = int.from_bytes(recv_all(1, keySoc), "big")

                recieve_key = recv_all(recieve_key_len, keySoc).decode()
                keyboard.press(recieve_key) 
                
            

        #  key released
        elif(recieve_event == b"2"):
            recieve_key_type = recv_all(1, keySoc)

            # not speacial letter
            if(recieve_key_type == b"1"):
                    
                scan_code_len = int.from_bytes(recv_all(1, keySoc), "big")
                win32api.keybd_event(scan_code, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)
            
            else:
                # special letter
                recieve_key_len = int.from_bytes(recv_all(1, keySoc), "big")

                recieve_key = recv_all(recieve_key_len, keySoc).decode()
                keyboard.release(recieve_key)

    # recieve all movements and do them yourself
 

def mouse_handeling():
    # for some reason its not exacly the width and heigh it should be
        #server_res = (server_width, server_heigh)
    server_res = (server_width, server_heigh)
    client_res = (client_width, client_heigth)

    while True:
        mouse_action = recv_all(1, mouseSoc)

        if mouse_action == b"0":  # Movement
            packed_data = recv_all(4, mouseSoc) # recive 2 bytes for x and 2 bytes for y
            control_com_x_Cords, control_com_y_Cords = struct.unpack('hh', packed_data)

            # Scale coordinates based on the resolution difference
            mapped_x = int(control_com_x_Cords * (client_res[0] / server_res[0]))
            mapped_y = int(control_com_y_Cords * (client_res[1] / server_res[1]))
            time.sleep(0.01)
            win32api.SetCursorPos((mapped_x, mapped_y))
    

        elif mouse_action == b"1":
            
            button_event = recv_all(1, mouseSoc)
            packed_data = recv_all(4, mouseSoc) # recive 2 bytes for x and 2 bytes for y
            x, y = struct.unpack('hh', packed_data)

            if button_event == b"3":
                button = "left"
            elif button_event == b"4":
                button = "right"
            pyautogui.mouseDown(mapped_x, mapped_y, button=button)

        elif mouse_action == b"2":
            button_event = recv_all(1, mouseSoc)
            packed_data = recv_all(4, mouseSoc) # recive 2 bytes for x and 2 bytes for y
            x, y = struct.unpack('hh', packed_data)

            if button_event == b"3":
                button = "left"
            elif button_event == b"4":
                button = "right"
            pyautogui.mouseUp(mapped_x,mapped_y, button=button)


def divide_image(image):
    width, height = image.size
    parts = []
    # Set grid size for 64 parts
    rows, cols = 8, 16
    # Calculate the size of each part

    part_width = width // cols
    part_height = height // rows

    for i in range(rows):
        for j in range(cols):
            left = j * part_width
            top = i * part_height
            right = (j + 1) * part_width
            bottom = (i + 1) * part_height

            # Adjust the last parts on the right and bottom edges
            right = (j + 1) * part_width
            bottom = (i + 1) * part_height

            parts.append(image.crop((left, top, right, bottom)))

    return parts



#added now
def encode_image_part(part):
    buf = io.BytesIO()
    part.save(buf, format="JPEG", quality=50, subsampling=2, optimize=True)
    data = buf.getvalue()
    if len(data) <= MAX_IMAGE_BYTES:
        return data

    buf = io.BytesIO()
    part.save(buf, format="JPEG", quality=30, subsampling=2, optimize=True)
    data = buf.getvalue()
    if len(data) <= MAX_IMAGE_BYTES:
        return data

    buf = io.BytesIO()
    part.save(buf, format="JPEG", quality=20, subsampling=2, optimize=True)
    return buf.getvalue()

def send_screenshot():
    while True:
        screenshot = ImageGrab.grab()
        image_parts = divide_image(screenshot)

        for idx, part in enumerate(image_parts):
            encoded = encode_image_part(part)
            packet = f"{idx:03}".encode() + encoded
            screenSoc.sendto(packet, (HOST, UDP_PORT))

        if len(packet) > MAX_UDP_PAYLOAD:
            print("BIG PACKET:", len(packet))
            
        screenSoc.sendto(b"1", (HOST, UDP_PORT))
        time.sleep(0.01)  # FPS cap

if __name__ == "__main__":
    # threads for key, mouse:
    key_thread = Thread(target=key_events)
    mouse_thread = Thread(target=mouse_handeling)
    screen_thread = Thread(target=send_screenshot)

    key_thread.start()
    mouse_thread.start()        
    screen_thread.start()

    key_thread.join()
    mouse_thread.join()
    screen_thread.join()

    #closing sockets:
    keySoc.close()
    mouseSoc.close()
    screenSoc.close() 