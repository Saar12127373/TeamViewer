Remote Desktop Control System
This project is a remote desktop solution providing real-time screen viewing and full keyboard/mouse control. It is built on a Client-Server architecture optimized for low latency and high reliability.

Network Architecture & Protocols
The system balances speed and data integrity by using two distinct communication channels:

TCP (Control Channel): Handles keyboard and mouse events. It ensures every command is delivered reliably and in the correct sequence.

UDP (Video Channel): Streams screen data using segmentation. By using UDP, the system bypasses Head-of-Line Blocking (common in TCP), significantly reducing latency for smoother visuals.

Environment: Developed in Python for Windows.

Core Functionality
Server Side (Remote Host)
Screen Capture: Captures desktop frames in real-time.

Transmission: Breaks frames into small segments and broadcasts them via UDP.

Command Listener: Receives client input via a TCP socket.

Input Injection: Executes commands on the host OS using the Windows API (SendInput).

Client Side (Controller)
Frame Reassembly: Collects UDP segments to reconstruct the full image.

Interactive Display: Renders the remote screen in a full-screen window.

Input Sampling: Captures local mouse/keyboard events to send to the server.

Resolution Scaling: Maps coordinates between client and server for precise mouse positioning.

Technical Highlights
Multithreading: Separates screen capture, network I/O, and input processing to eliminate bottlenecks.

Custom Binary Protocol: Uses the struct library to pack data into efficient binary packets.

Win32 API Integration: Interfaces directly with the OS for high-performance input injection.

Modular Design: Features a clean separation between Keyboard, Mouse, and Screen components.

Project Structure
Plaintext
project/
├── const.py             # System constants and configurations
├── protocol.py          # Custom packet definitions
├── server.py            # Main server logic
├── client.py            # Main client logic
└── components/          # Functional modules
    ├── keyboard_component.py
    ├── mouse_component.py
    └── screen_component.py
