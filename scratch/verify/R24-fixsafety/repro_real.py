import asyncio, os, subprocess, sys, tempfile, shutil, socket, time, urllib.request, json
import zendriver as zd
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

async def main():
    port = free_port()
    prof = tempfile.mkdtemp(prefix="r24prof_", dir=os.environ["SCRATCH"])
    proc = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", f"--remote-debugging-port={port}",
                             f"--user-data-dir={prof}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read(); break
            except Exception: time.sleep(0.1)
        print("chrome up on", port, "pid", proc.pid)
        try:
            zd.core.config.find_executable()
            print("find_executable found something:", zd.core.config.find_executable())
        except FileNotFoundError as e:
            print("find_executable: none on PATH (expected)")
        for label, coro_f in [
            ("zd.start(host,port)", lambda: zd.start(host="127.0.0.1", port=port)),
            ("Browser.create(host,port)", lambda: zd.Browser.create(host="127.0.0.1", port=port)),
        ]:
            try:
                b = await asyncio.wait_for(coro_f(), 30)
                v = await b.connection.send(zd.cdp.browser.get_version())
                print(label, "-> connected OK:", v[1])
                await b.connection.aclose()
                # do not stop the browser (we own it via proc); just disconnect
            except Exception as e:
                print(label, "-> raised", type(e).__name__, str(e)[:90])
        # create_from_undetected_chromedriver with a fake driver object
        class Svc:
            def stop(self): print("  fake service.stop called")
        class Opts: debugger_address = f"127.0.0.1:{port}"
        class Drv:
            options = Opts(); browser_pid = proc.pid; service = Svc(); user_data_dir = None
        try:
            b = await asyncio.wait_for(zd.util.create_from_undetected_chromedriver(Drv()), 30)
            v = await b.connection.send(zd.cdp.browser.get_version())
            print("create_from_undetected_chromedriver -> connected OK:", v[1])
            b._process_pid = None
            await b.connection.aclose()
        except Exception as e:
            print("create_from_undetected_chromedriver -> raised", type(e).__name__, str(e)[:90])
    finally:
        proc.terminate()
        try: proc.wait(10)
        except Exception: proc.kill()
        shutil.rmtree(prof, ignore_errors=True)

asyncio.run(main())
