import sys, os, tempfile, pathlib, zipfile, shutil, glob
import zendriver
from zendriver.core import util
from zendriver.core.config import Config
print("zendriver from", zendriver.__file__, sys.version.split()[0])
pts = list(util.circle(100, 0, radius=10, num=4))
print("circle(100,0):", pts)
pts = list(util.circle(100, 0.0001, radius=10, num=4))
print("circle(100,0.0001):", pts)
pts = list(util.circle(100, 50, radius=10, num=4))
print("circle(100,50):", pts)
pts = list(util.circle(100, radius=10, num=4))
print("circle(100):", pts)
# add_extension dir
root = pathlib.Path(tempfile.mkdtemp(prefix="bfref_ext_"))
(root/"manifest.json").write_text('{"manifest_version":3,"name":"x","version":"1"}')
(root/"web").mkdir(); (root/"web"/"manifest.webmanifest").write_text("{}")
c = Config(headless=True)
c.add_extension(root)
print("ext root", root, "-> loaded", c._extensions)
print("rglob order", list(root.rglob("manifest.*")))
# variant: only nested (intended use?)
root2 = pathlib.Path(tempfile.mkdtemp(prefix="bfref_ext2_"))
(root2/"1.0_0").mkdir(); (root2/"1.0_0"/"manifest.json").write_text("{}")
c2 = Config(headless=True); c2.add_extension(root2); print("only-nested root2 ->", c2._extensions)
# crx
crxdir = pathlib.Path(tempfile.mkdtemp(prefix="bfref_crx_"))
crx = crxdir/"ext.crx"
with zipfile.ZipFile(crx, "w") as z: z.writestr("manifest.json", '{"manifest_version":3,"name":"x","version":"1"}')
before = set(glob.glob(tempfile.gettempdir()+"/extension_*"))
c3 = Config(headless=True); c3.add_extension(crx)
print("crx ->", c3._extensions, "exists", os.path.isdir(c3._extensions[0]))
del c3
import gc; gc.collect()
after = set(glob.glob(tempfile.gettempdir()+"/extension_*"))
print("new extension_ dirs after Config gc:", after - before)
# cleanup
for d in after - before: shutil.rmtree(d)
for d in (root, root2, crxdir): shutil.rmtree(d)
