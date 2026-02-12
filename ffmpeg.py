# sender.py
import subprocess
import sys

# CHANGE THIS to the receiver's IP
HOST = "192.168.1.129"
PORT = 8091


FPS = 30
SCALE_WIDTH = 1280
BITRATE = "2500k"

# SRT caller URL
url = (
    f"srt://{HOST}:{PORT}"
    f"?mode=caller"
    f"&latency=80"
    f"&sndbuf=2097152"
)

cmd = [
    "ffmpeg",
    "-loglevel", "warning",

    # Capture (Windows)
    "-f", "gdigrab",
    "-framerate", str(FPS),
    "-i", "desktop",

    # Resize (keeps aspect ratio)
    "-vf", f"scale={SCALE_WIDTH}:-1",

    # Encode H.264 for low-latency
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "zerolatency",
    "-b:v", BITRATE,
    "-maxrate", BITRATE,
    "-bufsize", "500k",
    "-g", str(FPS),
    "-keyint_min", str(FPS),
    "-bf", "0",              # no B-frames

    # Transport
    "-f", "mpegts",
    url
]

print("SRT sender started (ffmpeg).")
print("Press Ctrl+C to stop.")

try:
    subprocess.run(cmd, check=False)
except FileNotFoundError:
    print("ffmpeg not found. Make sure FFmpeg is in PATH.")
    sys.exit(1)
















# receiver.py
import subprocess
import sys

# Listen on all interfaces
PORT = 8091

# SRT listener URL
url = f"srt://0.0.0.0:{PORT}?mode=listener&latency=80&rcvbuf=2097152"

cmd = [
    "ffplay",
    "-loglevel", "warning",

    # Low-latency playback tuning
    "-fflags", "nobuffer",
    "-flags", "low_delay",
    "-framedrop",
    "-sync", "ext",

    # Input
    url
]

print("SRT receiver started (ffplay).")
print("Waiting for sender... Close the window to stop.")

try:
    subprocess.run(cmd, check=False)
except FileNotFoundError:
    print("ffplay not found. Make sure FFmpeg is in PATH.")
    sys.exit(1)
