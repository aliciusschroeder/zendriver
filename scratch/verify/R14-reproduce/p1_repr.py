import os, sys, glob, copy, tempfile
import zendriver as zd
print("zendriver from", zd.__file__)
print("tempdir", tempfile.gettempdir())
def uc(): return sorted(glob.glob(os.path.join(tempfile.gettempdir(), "uc_*")))
for label, action in [("repr", repr), ("str", str), ("call", lambda c: c()), ("attr", lambda c: c.user_data_dir)]:
    c = zd.Config(headless=True, browser_executable_path="/bin/true")
    before = uc()
    print(f"[{label}] before: _user_data_dir={c._user_data_dir!r} custom={c.uses_custom_data_dir}")
    action(c)
    after = uc()
    print(f"[{label}] after : _user_data_dir={c._user_data_dir!r} custom={c.uses_custom_data_dir} new_dirs={sorted(set(after)-set(before))}")
    d1 = copy.deepcopy(c); d2 = copy.deepcopy(c)
    print(f"[{label}] deepcopies share path: {d1.user_data_dir == d2.user_data_dir == c._user_data_dir}  custom={d1.uses_custom_data_dir}")
# control: no repr
c = zd.Config(headless=True, browser_executable_path="/bin/true")
d1 = copy.deepcopy(c); d2 = copy.deepcopy(c)
print("[control] deepcopies distinct:", d1.user_data_dir != d2.user_data_dir, d1.user_data_dir, d2.user_data_dir)
print("leftover uc_ dirs:", uc())
