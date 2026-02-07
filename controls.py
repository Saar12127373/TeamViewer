import socket
import struct
import ctypes
import keyboard
from threading import Thread
from pynput import mouse

HOST = ""         # listen on all interfaces
PORT = 8090       # one TCP connection for both keyboard+mouse in this version

# ---------- helpers ----------
def recv_all(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data

def key_to_vk(key_char: str) -> int:
    # For single char keys only
    result = ctypes.windll.User32.VkKeyScanW(ord(key_char))
    vk = result & 0xFF
    return vk

# ---------- protocol ----------
# We'll send framed messages:
# [1 byte type][payload...]
#
# Types:
#  K_DOWN = b'K'  payload: [1 byte kind][...]
#  K_UP   = b'k'  payload: [1 byte kind][...]
#     kind = 1 -> single char => [1 byte vk]
#     kind = 2 -> named key  => [1 byte len][bytes name]
#
#  M_MOVE = b'M'  payload: [2 bytes x][2 bytes y]  (signed short)
#  M_DOWN = b'D'  payload: [1 byte btn][2 bytes x][2 bytes y]
#  M_UP   = b'U'  payload: [1 byte btn][2 bytes x][2 bytes y]
#     btn: 1=left, 2=right

K_DOWN, K_UP = b'K', b'k'
M_MOVE, M_DOWN, M_UP = b'M', b'D', b'U'

def send_key(sock: socket.socket, down: bool, name: str):
    msg_type = K_DOWN if down else K_UP

    if len(name) == 1:
        kind = b"\x01"
        vk = key_to_vk(name)
        sock.sendall(msg_type + kind + bytes([vk]))
    else:
        kind = b"\x02"
        bname = name.encode("utf-8", errors="ignore")
        if len(bname) > 255:
            bname = bname[:255]
        sock.sendall(msg_type + kind + bytes([len(bname)]) + bname)

def send_mouse_move(sock: socket.socket, x: int, y: int):
    sock.sendall(M_MOVE + struct.pack("!hh", x, y))

def send_mouse_btn(sock: socket.socket, down: bool, btn: int, x: int, y: int):
    msg_type = M_DOWN if down else M_UP
    sock.sendall(msg_type + bytes([btn]) + struct.pack("!hh", x, y))

# ---------- threads ----------
def keyboard_thread(sock: socket.socket):
    while True:
        ev = keyboard.read_event()
        if ev.event_type == "down":
            send_key(sock, True, ev.name)
        elif ev.event_type == "up":
            send_key(sock, False, ev.name)

def mouse_thread(sock: socket.socket):
    def on_move(x, y):
        send_mouse_move(sock, int(x), int(y))

    def on_click(x, y, button, pressed):
        btn = 1 if button == mouse.Button.left else 2
        send_mouse_btn(sock, pressed, btn, int(x), int(y))

    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        listener.join()

# ---------- main ----------
def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[SERVER] listening on {HOST}:{PORT} ...")

    client, addr = srv.accept()
    print(f"[SERVER] client connected: {addr}")

    t1 = Thread(target=keyboard_thread, args=(client,), daemon=True)
    t2 = Thread(target=mouse_thread, args=(client,), daemon=True)
    t1.start()
    t2.start()

    # keep process alive
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()
