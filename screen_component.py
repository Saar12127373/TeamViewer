import cv2
import numpy as np
import io
from PIL import Image, ImageGrab
from const import ROWS, COLS

class ScreenSender:
    def __init__(self, sock, addr, stop_event):
        self.sock = sock
        self.addr = addr
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            img = ImageGrab.grab()
            w, h = img.size
            pw, ph = w // COLS, h // ROWS
            
            for i in range(ROWS):
                for j in range(COLS):
                    part = img.crop((j*pw, i*ph, (j+1)*pw, (i+1)*ph))
                    buf = io.BytesIO()
                    part.save(buf, format='JPEG', quality=40)
                    # Fixed 3-digit ID for ordering
                    packet = f"{(i*COLS+j):03}".encode() + buf.getvalue()
                    self.sock.sendto(packet, self.addr)
            
            self.sock.sendto(b"1", self.addr) # Frame End Marker

class ScreenReceiver:
    def __init__(self, sock, win_name, stop_event):
        self.sock = sock
        self.win_name = win_name
        self.stop_event = stop_event
        self.parts = [None] * (ROWS * COLS)

    def run(self):
        cv2.namedWindow(self.win_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        while not self.stop_event.is_set():
            while True:
                data, _ = self.sock.recvfrom(65535)
                if data == b"1": break # End of frame
                idx = int(data[:3].decode())
                self.parts[idx] = data[3:]
            
            self.render()

    def render(self):
        try:
            # Reconstruct correctly using fixed indices
            grid = []
            for p in self.parts:
                if p is None: return 
                grid.append(Image.open(io.BytesIO(p)))
            
            pw, ph = grid[0].size
            full_img = Image.new('RGB', (pw * COLS, ph * ROWS))
            
            for i in range(ROWS):
                for j in range(COLS):
                    full_img.paste(grid[i * COLS + j], (j * pw, i * ph))
            
            cv_img = cv2.cvtColor(np.array(full_img), cv2.COLOR_RGB2BGR)
            
            # --- FORCING THE WINDOW TO THE FRONT ---
            cv2.imshow(self.win_name, cv_img)
            
            # This forces the window to stay on top of all other apps
            cv2.setWindowProperty(self.win_name, cv2.WND_PROP_TOPMOST, 1)
            
            cv2.waitKey(1)
        except: pass