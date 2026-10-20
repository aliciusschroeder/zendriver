import zendriver
from zendriver import ContraDict, cdict
print("zendriver from", zendriver.__file__)
ARGS = {"clear": (), "items": (), "get": ("a",), "values": (), "keys": (), "copy": (), "update": ({},), "pop": ("a",), "setdefault": ("z", 1), "popitem": ()}
for k, args in ARGS.items():
    cd = ContraDict({k: "v", "a": 1}, silent=True)
    try:
        getattr(cd, k)(*args); ok = "ok"
    except Exception as e:
        ok = f"{type(e).__name__}: {e}"
    print(f"key={k!r}: cd.{k}{args} -> {ok}")
cd = ContraDict({"a": 1, "href": "x"}, silent=True)
print("control", cd.items(), cd.get("a"), cd.href)
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    ContraDict({"clear": "all"})
    print("warnings emitted on non-silent:", len(w))
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    c = ContraDict(silent=True); c["clear"] = "all"
    print("warnings on setitem:", len(w), "clear attr ->", repr(c.clear))
# dict methods via class still work (workaround)
c = ContraDict({"items": "x", "a": 1}, silent=True)
print("workaround dict.items(c):", list(dict.items(c)))
