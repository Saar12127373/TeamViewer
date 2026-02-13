import socket
import ctypes
import threading
from const import *
from protocol import recv_all
from components.keyboard_component import KeyboardReceiver
from components.mouse_component import MouseReceiver
from components.screen_component import ScreenSender

def main():
    stop_event = threading.Event()

    k_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    k_sock.connect((TARGET_HOST, TCP_PORT))
    
    m_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    m_sock.connect((TARGET_HOST, TCP_PORT))

    # Get server resolution for mapping
    s_w = int.from_bytes(recv_all(m_sock, 2), "big")
    s_h = int.from_bytes(recv_all(m_sock, 2), "big")
    
    user32 = ctypes.windll.user32
    c_res = (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Initialize Components
    kb = KeyboardReceiver(k_sock, stop_event)
    ms = MouseReceiver(m_sock, stop_event, (s_w, s_h), c_res)
    sc = ScreenSender(udp_sock, (TARGET_HOST, UDP_PORT), stop_event)

    # Launch
    threading.Thread(target=kb.run, daemon=True).start()
    threading.Thread(target=ms.run, daemon=True).start()
    
    try:
        sc.run() # Screen sending is usually the heaviest, keep on main thread
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()