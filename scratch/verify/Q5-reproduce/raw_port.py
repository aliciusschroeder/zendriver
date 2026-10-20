import os, socket, subprocess, sys, time, tempfile, shutil, fcntl, termios, struct
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
d = tempfile.mkdtemp(dir=os.path.dirname(os.path.abspath(__file__)))
p = subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", f"--user-data-dir={d}", f"--remote-debugging-port={port}", "--remote-debugging-host=127.0.0.1", "about:blank"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(3)
n = struct.unpack("i", fcntl.ioctl(p.stderr.fileno(), termios.FIONREAD, struct.pack("i", 0)))[0]
os.set_blocking(p.stderr.fileno(), False)
data = os.read(p.stderr.fileno(), 65536).decode(errors="replace")
print("alive:", p.poll() is None, "bytes waiting:", n)
print([l for l in data.splitlines() if "devtools" in l.lower()])
p.kill(); p.wait(); shutil.rmtree(d, ignore_errors=True); s.close()
