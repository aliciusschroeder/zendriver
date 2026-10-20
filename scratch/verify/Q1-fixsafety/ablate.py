import re, sys, subprocess, shutil, os
D = sys.argv[1]
diff = open(f"{D}/prototype.diff").read()
# split hunks
header, *hunks = re.split(r"(?m)^(?=@@ )", diff)
names = ["tx_call", "aopen_revive", "receive_except", "callback_raise"]
for skip in range(len(hunks)):
    vd = f"{D}/ablate_{names[skip]}"
    shutil.rmtree(vd, ignore_errors=True)
    shutil.copytree(f"{D}/orig", f"{vd}/zendriver_root")
    patch = header + "".join(h for i, h in enumerate(hunks) if i != skip)
    p = subprocess.run(["patch", "-p1", "-d", f"{vd}/zendriver_root", "-s"], input=patch.replace("--- orig/", "--- a/").replace("+++ pkg/", "+++ b/"), text=True, capture_output=True)
    print(names[skip], "patch rc", p.returncode, p.stdout, p.stderr)
