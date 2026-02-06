# server.py  (YOUR PC - "server": shows video + sends keyboard/mouse to client)
import struct
import socket
import ctypes
import time
import subprocess
from threading import Thread
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse

HOST = ""          # listen on all interfaces for TCP control
PORT = 8090        # TCP control port (keyboard/mouse)
SRT_PORT = 8091    # SRT video port (UDP underneath)
SRT_LATENCY_MS = 80

running = True


# --- TCP setup ---
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.bind((HOST, PORT))
soc.listen(2)
print("Server is listening!")

key_sock, client_addr1 = soc.accept()
print("Keyboard channel connected:", client_addr1)

mouse_soc, client_addr2 = soc.accept()
print("Mouse channel connected:", client_addr2)


# --- helpers ---
def recv_all(length, client_sock):
    content = b""
    while length > 0:
        temp = client_sock.recv(length)
        if not temp:
            raise ConnectionError("Socket closed")
        length -= len(temp)
        content += temp
    return content

def keyTo_scanCode(ch: str) -> int:
    result = ctypes.windll.User32.VkKeyScanW(ord(ch))
    vk_key = result & 0xFF
    return vk_key

def get_screen_resolution():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def send_cords(x, y):
    packed = struct.pack('hh', int(x), int(y))
    mouse_soc.sendall(packed)


# --- send server resolution once (used by client to scale mouse coords) ---
server_width, server_height = get_screen_resolution()
print("Server resolution:", server_width, server_height)
mouse_soc.sendall(int(server_width).to_bytes(2, "big"))
mouse_soc.sendall(int(server_height).to_bytes(2, "big"))


# --- VIDEO: SRT receiver (ffplay) ---
def start_video_receiver():
    # SRT listener URL (note: SRT runs over UDP)
    url = f"srt://0.0.0.0:{SRT_PORT}?mode=listener&latency={SRT_LATENCY_MS}&rcvbuf=2097152"

    cmd = [
        "ffplay",
        "-loglevel", "warning",
        "-fs",
        "-noborder",
        "-flags", "low_delay",
        "-sync", "ext",
        "-framedrop",
        "-sync", "ext",
        url
    ]

    print("Starting SRT receiver (ffplay). Waiting for sender...")
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("ffplay not found. Make sure FFmpeg is installed and in PATH.")


# --- KEYBOARD (suppress local input, send to client) ---
def keyBoard_Events():
    global running

    def on_press(key):
        global running
        # F12 stops the whole program
        if key == pynput_keyboard.Key.f12:
            running = False
            return False

        try:
            if hasattr(key, 'char') and key.char is not None:
                key_sock.sendall(b"1")  # Event: Down
                key_sock.sendall(b"1")  # Mode: Char
                scan_code = keyTo_scanCode(key.char)
                key_sock.sendall(int(scan_code).to_bytes(1, "big"))
            else:
                name = str(key).replace('Key.', '')
                key_sock.sendall(b"1")  # Event: Down
                key_sock.sendall(b"2")  # Mode: Special
                key_sock.sendall(len(name).to_bytes(1, "big"))
                key_sock.sendall(name.encode())
        except:
            pass

    def on_release(key):
        if key == pynput_keyboard.Key.f12:
            return False

        try:
            if hasattr(key, 'char') and key.char is not None:
                key_sock.sendall(b"2")  # Event: Up
                key_sock.sendall(b"1")  # Mode: Char
                scan_code = keyTo_scanCode(key.char)
                key_sock.sendall(int(scan_code).to_bytes(1, "big"))
            else:
                name = str(key).replace('Key.', '')
                key_sock.sendall(b"2")  # Event: Up
                key_sock.sendall(b"2")  # Mode: Special
                key_sock.sendall(len(name).to_bytes(1, "big"))
                key_sock.sendall(name.encode())
        except:
            pass

    with pynput_keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True) as listener:
        listener.join()


# --- MOUSE (suppress local input, send to client) ---
def mouse_managment():
    def on_move(x, y):
        global last_send
        try:
            now = time.time()
            if now - last_send < 0.01:
                return
            last_send = now

            mouse_soc.sendall(b"0")
            send_cords(x, y)

        except Exception as e:
            print("on_move error:", e)
            # לא מחזירים False כדי לא לעצור את ה-listener
            return

    def on_click(x, y, button, pressed):
        try:
            mouse_soc.sendall(b"1" if pressed else b"2")
            btn = b"3" if button == pynput_mouse.Button.left else b"4"
            mouse_soc.sendall(btn)
            send_cords(x, y)
        except Exception as e:
            print("on_click error:", e)

    with pynput_mouse.Listener(on_move=on_move, on_click=on_click, suppress=False) as listener:
        listener.join()


def main():
    global running

    # threads
    video_thread = Thread(target=start_video_receiver, daemon=True)
    keyboard_thread = Thread(target=keyBoard_Events, daemon=True)
    mouse_thread = Thread(target=mouse_managment, daemon=True)

    video_thread.start()
    keyboard_thread.start()
    mouse_thread.start()

    print("Running. Press F12 to stop.")

    # wait until F12 stops
    try:
        while running:
            time.sleep(0.1)
    finally:
        # close sockets
        try: key_sock.close()
        except: pass
        try: mouse_soc.close()
        except: pass
        try: soc.close()
        except: pass
        print("Server stopped.")


if __name__ == "__main__":
    main()
