import keyboard
import ctypes
import win32api
import win32con
from protocol import recv_all

class KeyboardSender:
    def __init__(self, sock, stop_event):
        self.sock = sock
        self.stop_event = stop_event

    def start_listening(self):
        while not self.stop_event.is_set():
            event = keyboard.read_event()
            # Send Type: b"1" for down, b"2" for up
            self.sock.sendall(b"1" if event.event_type == "down" else b"2")
            
            if len(event.name) == 1:
                self.sock.sendall(b"1") # Normal char marker
                vk = ctypes.windll.User32.VkKeyScanW(ord(event.name)) & 0xFF
                self.sock.sendall(int(vk).to_bytes(1, "big"))
            else:
                self.sock.sendall(b"2") # Special key marker
                self.sock.sendall(len(event.name).to_bytes(1, "big"))
                self.sock.sendall(event.name.encode())

class KeyboardReceiver:
    def __init__(self, sock, stop_event):
        self.sock = sock
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                event_type = recv_all(self.sock, 1)
                key_cat = recv_all(self.sock, 1)
                
                if key_cat == b"1": # Normal
                    vk = int.from_bytes(recv_all(self.sock, 1), "big")
                    flag = 0 if event_type == b"1" else win32con.KEYEVENTF_KEYUP
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_EXTENDEDKEY | flag, 0)
                else: # Special
                    length = int.from_bytes(recv_all(self.sock, 1), "big")
                    name = recv_all(self.sock, length).decode()
                    if event_type == b"1": keyboard.press(name)
                    else: keyboard.release(name)
            except: break