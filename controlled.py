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
import cv2



HOST = "192.168.1.128"
TCP_PORT = 8090
UDP_PORT = 8091

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


# open file and ensuring it will me empty


#if i could have only used english letters there could have been a better solution, using a dict:
# using the fact that every key has a key code witch could be used to adf yo sup my g 



# keys_dict = {160: 'shift', 65: 'a', 91: 'cmd', 164: 'alt_l', 32: 'space', 165: 'alt_gr', 93: 'menu', 226: '\\', 37: 'left', 40: 'down', 39: 'right', 96: '0', 97: '1', 49: '1', 98: '2', 99: '3', 76: 'l', 27: 'esc', 100: '4', 101: '5', 102:'6', 103:'7', 104:'8', 105:'9', 110: '.', 13: 'enter', 107: '+', 109: '-', 106: '*', 111: '/', 162: 'ctrl_l', 86: '\x16', 190: '.', 90: 'z', 88: 'x', 67: 'c', 66: 'b', 78: 'n', 77: 'm', 188: ',', 191: '/', 161: 'shift_r', 38: 'up', 20: 'caps_lock', 83: 's', 68: 'd', 70: 'f', 72: 'h', 71: 'g', 74: 'j', 75: 'k', 186: ';', 222: "'", 9: 'tab', 81: 'q', 87: 'w', 69: 'e', 82: 'r', 84: 't', 89: 'y', 85: 'u', 73: 'i', 79: 'o', 80: 'p', 219: '[', 221: ']', 220: '\\', 46: 'delete', 35: 'end', 34: 'page_down', 53: '5', 192: '`', 50: '2', 51: '3', 52: '4', 54: '6', 55: '7', 56: '8', 57: '9', 48: '0', 189: '-', 187: '=', 8: 'backspace', 45: 'insert', 36: 'home', 33: 'page_up', 173: 'media_volume_mute', 174: 'media_volume_down', 175: 'media_volume_up', 177: 'media_previous', 179: 'media_play_pause', 176: 'media_next', 132: 'f21', 44: 'print_screen', 19: 'pause', 145: 'scroll_lock', 183: 'f'}


server_width = int.from_bytes(recv_all(2, mouseSoc))
server_heigh = int.from_bytes(recv_all(2, mouseSoc))

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
    server_res  = (1930, 1105)
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
            if j == cols - 1:
                right = width
            if i == rows - 1:
                bottom = height

            parts.append(image.crop((left, top, right, bottom)))

    return parts

def encode_image_part(part):
    byte_arr = io.BytesIO()
    part.save(byte_arr, format='PNG')
    return byte_arr.getvalue()

#try to make screen soc tcp when sending 1 byte
def send_screenshot():
    while True:    
        screenshot = ImageGrab.grab()     
        image_parts = divide_image(screenshot)
        encoded_parts = [encode_image_part(part) for part in image_parts]

        for idx, part in enumerate(encoded_parts):
            packet = f"{idx:03}".encode() + part

            screenSoc.sendto(packet, (HOST, UDP_PORT))

        screenSoc.sendto(b"1", (HOST, UDP_PORT))
        cv2.waitKey(4)





if __name__ == "_main_":
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