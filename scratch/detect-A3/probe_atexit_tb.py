import asyncio, os, traceback, shutil
import zendriver as zd

state = {}
class B(zd.Browser):
    async def _atexit_cleanup(self):
        try:
            await super()._atexit_cleanup()
        except BaseException:
            traceback.print_exc(limit=-3)
            raise

async def main():
    b = await B.create(headless=True)
    state["udd"] = b.config.user_data_dir

asyncio.run(main())
print("temp profile exists after asyncio.run:", os.path.exists(state["udd"]))
shutil.rmtree(state["udd"], ignore_errors=True)
