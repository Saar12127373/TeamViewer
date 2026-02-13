from pynput import mouse
import pyautogui
import win32api
import struct
from protocol import recv_all, pack_coords, unpack_coords

class MouseSender:
    def __init__(self, sock, stop_event):
        self.sock = sock
        self.stop_event = stop_event

    def on_move(self, x, y):
        self.sock.sendall(b"0")
        self.sock.sendall(pack_coords(x, y))

    def on_click(self, x, y, button, pressed):
        self.sock.sendall(b"1" if pressed else b"2")
        btn_id = b"3" if button == mouse.Button.left else b"4"
        self.sock.sendall(btn_id)
        self.sock.sendall(pack_coords(x, y))

    def start(self):
        with mouse.Listener(on_move=self.on_move, on_click=self.on_click) as listener:
            while not self.stop_event.is_set():
                listener.join(0.1)

class MouseReceiver:
    def __init__(self, sock, stop_event, s_res, c_res):
        self.sock = sock
        self.stop_event = stop_event
        self.s_res = s_res # Server res (sender)
        self.c_res = c_res # Client res (executor)

    def run(self):
        while not self.stop_event.is_set():
            try:
                action = recv_all(self.sock, 1)
                if action == b"0": # Move
                    x, y = unpack_coords(recv_all(self.sock, 4))
                    mx = int(x * (self.c_res[0] / self.s_res[0]))
                    my = int(y * (self.c_res[1] / self.s_res[1]))
                    win32api.SetCursorPos((mx, my))
                elif action in [b"1", b"2"]: # Click/Release
                    btn_code = recv_all(self.sock, 1)
                    x, y = unpack_coords(recv_all(self.sock, 4))
                    btn = "left" if btn_code == b"3" else "right"
                    # Note: Using your original logic where x,y aren't re-mapped for clicks
                    # but are received from the buffer.
                    if action == b"1": pyautogui.mouseDown(button=btn)
                    else: pyautogui.mouseUp(button=btn)
            except: break