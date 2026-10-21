"""custom profile: compare the profile's exit_type after (a) normal stop() and (b) a
start() that fails late (injected in _read_headless_user_agent)."""
import asyncio, json, os, shutil, sys, tempfile
import zendriver as zd
CHROME = shutil.which("chromium")
mode = sys.argv[1]
async def main():
    udd = tempfile.mkdtemp(prefix="custom_prof_")
    if mode == "failed_start":
        async def boom(self):
            await self.connection.send(zd.cdp.browser.get_version())
            raise RuntimeError("late failure")
        zd.Browser._read_headless_user_agent = boom
        try:
            await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME, user_data_dir=udd)
        except RuntimeError as e:
            print("start raised", e)
    else:
        b = await zd.start(headless=True, sandbox=False, browser_executable_path=CHROME, user_data_dir=udd)
        await b.get("data:text/html,<p>x</p>")
        await b.stop()
    prefs = json.load(open(os.path.join(udd, "Default", "Preferences")))
    print(mode, "exit_type:", prefs.get("profile", {}).get("exit_type"), "exited_cleanly:", prefs.get("profile", {}).get("exited_cleanly"))
    shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
