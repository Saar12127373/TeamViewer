# Remote Desktop Control System

This project implements a remote desktop solution that enables real-time screen viewing and full keyboard/mouse control of a remote Windows machine. It uses a **Client-Server architecture** optimized for low latency and reliability.



---

## Network Architecture & Protocols

The system utilizes two distinct communication channels to balance speed and data integrity:

* **TCP (Control Channel):** Handles keyboard and mouse input events. TCP ensures that every user command is delivered reliably and in the correct sequence.
* **UDP (Video Channel):** Streams screen data using **segmentation**. UDP is used to bypass *Head-of-Line Blocking*, significantly reducing latency for a smoother visual experience.

**Environment:** Developed in **Python** for **Windows** environments.

---

## Core Functionality

### Server Side (Remote Host)
* **Screen Capture:** Captures the desktop frames in real-time.
* **Segmentation:** Breaks each frame into smaller chunks (segments) and broadcasts them via UDP.
* **Command Listener:** Receives input data from the client via the TCP socket.
* **Input Injection:** Executes the received commands on the host OS using the **Windows API (SendInput)**.

### Client Side (Controller)
* **Frame Reassembly:** Collects UDP segments and reconstructs them into a complete image frame.
* **Interactive Display:** Renders the remote screen in a full-screen window.
* **Input Sampling:** Monitors local mouse and keyboard events to send them to the server.
* **Resolution Scaling:** Maps coordinates between client and server resolutions for precise mouse positioning.

---

## Technical Highlights

* **Multithreading:** Separates screen capture, network I/O, and input processing to prevent performance bottlenecks.
* **Custom Binary Protocol:** Uses the `struct` library to pack data into efficient binary packets.
* **Low-Level Integration:** Interfaces directly with the **Win32 API** for high-performance input injection.
* **Modular Design:** Clean separation of concerns between `Keyboard`, `Mouse`, and `Screen` components.

---

## Project Structure

```text
project/
├── const.py             # System constants and configurations
├── protocol.py          # Custom packet definitions
├── server.py            # Main server logic
├── client.py            # Main client logic
└── components/          # Functional modules
    ├── keyboard_component.py
    ├── mouse_component.py
    └── screen_component.py
