from pynput import mouse
import pyautogui
import win32api
from protocol import recv_all, pack_coords, unpack_coords

class MouseSender:
    def __init__(self, sock, stop_event):
        self.sock = sock
        self.stop_event = stop_event

    def on_move(self, x, y):
        # We use a non-blocking check to see if we should stop
        if self.stop_event.is_set():
            return False 
        self.sock.sendall(b"0")
        self.sock.sendall(pack_coords(x, y))

    def on_click(self, x, y, button, pressed):
        if self.stop_event.is_set():
            return False
        self.sock.sendall(b"1" if pressed else b"2")
        btn_id = b"3" if button == mouse.Button.left else b"4"
        self.sock.sendall(btn_id)
        self.sock.sendall(pack_coords(x, y))

    def start(self):
        with mouse.Listener(on_move=self.on_move, on_click=self.on_click) as listener:
            # This keeps the listener alive until stop_event is set
            while not self.stop_event.is_set():
                listener.join(0.1)

class MouseReceiver:
    def __init__(self, sock, stop_event, s_res, c_res):
        self.sock = sock
        self.stop_event = stop_event
        self.s_res = s_res # Server resolution
        self.c_res = c_res # Client resolution

    def run(self):
        while not self.stop_event.is_set():
            try:
                action = recv_all(self.sock, 1)
                if not action: break # Connection closed
                
                if action == b"0": # Move event
                    data = recv_all(self.sock, 4)
                    x, y = unpack_coords(data)
                    # Mapping logic to ensure mouse reaches corners on different screens
                    mx = int(x * (self.c_res[0] / self.s_res[0]))
                    my = int(y * (self.c_res[1] / self.s_res[1]))
                    win32api.SetCursorPos((mx, my))
                    
                elif action in [b"1", b"2"]: # Click/Release event
                    btn_code = recv_all(self.sock, 1)
                    data = recv_all(self.sock, 4)
                    x, y = unpack_coords(data)
                    
                    # Map coordinates for clicks too so they hit the right button
                    mx = int(x * (self.c_res[0] / self.s_res[0]))
                    my = int(y * (self.c_res[1] / self.s_res[1]))
                    
                    btn = "left" if btn_code == b"3" else "right"
                    if action == b"1": 
                        pyautogui.mouseDown(x=mx, y=my, button=btn)
                    else: 
                        pyautogui.mouseUp(x=mx, y=my, button=btn)
            except Exception as e:
                print(f"Mouse Error: {e}")
                break