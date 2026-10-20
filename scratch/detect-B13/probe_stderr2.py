import socket, subprocess, time, os, fcntl, termios, array
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
p = subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}", "--user-data-dir=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/detect-B13/ud", "about:blank"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(3)
buf = array.array('i', [0]); fcntl.ioctl(p.stderr.fileno(), termios.FIONREAD, buf)
print("alive:", p.poll() is None, "bytes waiting in stderr pipe:", buf[0])
os.set_blocking(p.stderr.fileno(), False)
data = os.read(p.stderr.fileno(), buf[0]).decode()
print([l for l in data.splitlines() if "dbus" not in l][:5])
p.kill(); p.wait()
