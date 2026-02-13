import socket
import ctypes
import threading
from const import *
from components.keyboard_component import KeyboardSender
from components.mouse_component import MouseSender
from components.screen_component import ScreenReceiver

def main():
    stop_event = threading.Event()
    
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((SERVER_BIND_HOST, TCP_PORT))
    server_sock.listen(1)
    print("Server Listening...")

    key_conn, _ = server_sock.accept()
    mouse_conn, _ = server_sock.accept()

    # Resolution Exchange
    user32 = ctypes.windll.user32
    res = (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    mouse_conn.sendall(int(res[0]).to_bytes(2, "big"))
    mouse_conn.sendall(int(res[1]).to_bytes(2, "big"))

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((SERVER_BIND_HOST, UDP_PORT))

    # Initialize Components
    kb = KeyboardSender(key_conn, stop_event)
    ms = MouseSender(mouse_conn, stop_event)
    sc = ScreenReceiver(udp_sock, WIN_NAME, stop_event)

    # Launch Threads (Daemon=True for safety)
    threading.Thread(target=kb.start_listening, daemon=True).start()
    threading.Thread(target=sc.run, daemon=True).start()
    
    try:
        ms.start() # Blocking call for pynput
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()