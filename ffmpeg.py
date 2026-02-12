# sender.py
import subprocess
import sys

# CHANGE THIS to the receiver's IP
HOST = "192.168.1.129"
PORT = 8091

# Tuning knobs
FPS = 30
SCALE_WIDTH = 1280     # try 960 / 1280 / 1600
BITRATE = "2500k"      # try 1500k..4000k

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
