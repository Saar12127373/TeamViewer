# server.py  (YOUR PC - "server": shows video + sends keyboard/mouse to client)

import struct
import socket
import ctypes
import time
import subprocess
from threading import Thread
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse

HOST = ""          # listen on all interfaces
PORT = 8090        # TCP control port
SRT_PORT = 8091    # SRT video port
SRT_LATENCY_MS = 120

running = True

# Control toggle: when False, we DON'T suppress or send events
control_enabled = True

# mouse throttle
last_send = 0.0
MOUSE_SEND_INTERVAL = 0.02  # 50 Hz (less laggy than spamming)


# --- TCP setup ---
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
soc.bind((HOST, PORT))
soc.listen(5)
print(f"Server listening on TCP {PORT}...")

def recv_all(length: int, s: socket.socket) -> bytes:
    data = b""
    while length > 0:
        chunk = s.recv(length)
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
        length -= len(chunk)
    return data

def get_screen_resolution():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def send_cords(x: int, y: int):
    # int32 so it won't overflow
    mouse_soc.sendall(struct.pack("ii", int(x), int(y)))

# ---- Accept channels with handshake (K=keyboard, M=mouse) ----
channels = {}
while len(channels) < 2:
    s, addr = soc.accept()
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    tag = recv_all(1, s)  # b"K" or b"M"
    channels[tag] = s
    print("Connected channel", tag, addr)

key_sock = channels[b"K"]
mouse_soc = channels[b"M"]

# --- send server resolution once (used by client to scale mouse coords) ---
server_width, server_height = get_screen_resolution()
print("Server resolution:", server_width, server_height)

# send as 4 bytes each (safer than 2)
mouse_soc.sendall(int(server_width).to_bytes(4, "big"))
mouse_soc.sendall(int(server_height).to_bytes(4, "big"))


# --- VIDEO: SRT receiver (ffplay) ---
def start_video_receiver():
    url = f"srt://0.0.0.0:{SRT_PORT}?mode=listener&latency={SRT_LATENCY_MS}&rcvbuf=2097152"

    cmd = [
        "ffplay",
        "-loglevel", "warning",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-framedrop",
        "-sync", "ext",
        "-fs",
        "-noborder",
        url
    ]
    print("Starting SRT receiver (ffplay). Waiting for sender...")
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("ffplay not found. Make sure FFmpeg is installed and in PATH.")


# --- Keyboard protocol: send key names only ---
def key_name_from_pynput(key):
    # char keys: 'a', '1', etc.
    if hasattr(key, "char") and key.char:
        return key.char
    # special keys: Key.enter -> "enter"
    return str(key).replace("Key.", "")

def send_key(event_byte: bytes, name: str):
    # event_byte: b"1" down, b"2" up
    data = name.encode("utf-8")
    key_sock.sendall(event_byte)
    key_sock.sendall(len(data).to_bytes(2, "big"))
    key_sock.sendall(data)

# --- KEYBOARD (suppress local input, send to client) ---
def keyboard_events():
    global running, control_enabled

    def on_press(key):
        nonlocal_listener_stop = False

        # F12 stops everything
        if key == pynput_keyboard.Key.f12:
            running = False
            return False

        # F10 toggles control mode (so you can "free" your PC)
        if key == pynput_keyboard.Key.f10:
            control_enabled = not control_enabled
            print("control_enabled =", control_enabled)
            return

        if not control_enabled:
            return

        try:
            send_key(b"1", key_name_from_pynput(key))
        except:
            pass

    def on_release(key):
        if key == pynput_keyboard.Key.f12:
            return False

        if not control_enabled:
            return

        try:
            send_key(b"2", key_name_from_pynput(key))
        except:
            pass

    # suppress=True blocks local keyboard input while enabled
    with pynput_keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True) as listener:
        listener.join()


# --- MOUSE (suppress local input, send to client) ---
def mouse_management():
    global last_send, running, control_enabled

    def on_move(x, y):
        global last_send
        if not control_enabled:
            return
        try:
            now = time.time()
            if now - last_send < MOUSE_SEND_INTERVAL:
                return
            last_send = now

            mouse_soc.sendall(b"0")  # move
            send_cords(x, y)
        except Exception as e:
            print("on_move error:", e)

    def on_click(x, y, button, pressed):
        if not control_enabled:
            return
        try:
            mouse_soc.sendall(b"1" if pressed else b"2")  # down/up
            btn = b"3" if button == pynput_mouse.Button.left else b"4"
            mouse_soc.sendall(btn)
            send_cords(x, y)
        except Exception as e:
            print("on_click error:", e)

    # suppress=True blocks local mouse while enabled
    with pynput_mouse.Listener(on_move=on_move, on_click=on_click, suppress=True) as listener:
        listener.join()


def main():
    global running

    video_thread = Thread(target=start_video_receiver, daemon=True)
    keyboard_thread = Thread(target=keyboard_events, daemon=True)
    mouse_thread = Thread(target=mouse_management, daemon=True)

    video_thread.start()
    keyboard_thread.start()
    mouse_thread.start()

    print("Running. F12 = stop. F10 = toggle control mode (freeze/unfreeze local input).")

    try:
        while running:
            time.sleep(0.1)
    finally:
        for s in (key_sock, mouse_soc, soc):
            try:
                s.close()
            except:
                pass
        print("Server stopped.")


if __name__ == "__main__":
    main()
