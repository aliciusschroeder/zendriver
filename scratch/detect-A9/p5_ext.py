import zendriver as zd, zipfile, os, tempfile, glob, sys
cfg = zd.Config(browser_executable_path="/x")
cfg.add_extension(sys.argv[1])
print("extension path chosen:", cfg._extensions)
# crx leak
crx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "e.crx")
with zipfile.ZipFile(crx, "w") as z:
    z.writestr("manifest.json", '{"manifest_version":3,"name":"x","version":"1"}')
before = set(glob.glob(os.path.join(tempfile.gettempdir(), "extension_*")))
for _ in range(3):
    c = zd.Config(browser_executable_path="/x"); c.add_extension(crx); del c
after = set(glob.glob(os.path.join(tempfile.gettempdir(), "extension_*")))
print("leaked extension temp dirs:", len(after - before))
for d in after - before:
    import shutil; shutil.rmtree(d)
