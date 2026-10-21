import copy
import json
import pickle
import sys
import warnings

import zendriver
from zendriver import ContraDict

print("zendriver from", zendriver.__file__, sys.version.split()[0])


def t(label, fn):
    try:
        r = fn()
        print(f"OK   {label}: {r!r}"[:200])
    except Exception as e:
        print(f"FAIL {label}: {type(e).__name__}: {e}"[:200])


methods = ["clear", "copy", "fromkeys", "get", "items", "keys", "pop", "popitem", "setdefault", "update", "values"]
for m in methods:
    cd = ContraDict({m: "v", "a": 1}, silent=True)
    t(f"cd.{m} is callable", lambda: callable(getattr(cd, m)))

cd = ContraDict({"Items": "I", "GET": "G", "class": "c", "data-id": "d", "a.b": "ab", "mro": "M", "title": "T", "id": 1}, silent=True)
for k in ["Items", "GET", "class", "data-id", "a.b", "mro", "title", "id"]:
    t(f"getattr(cd,{k!r})", lambda: getattr(cd, k))

for k in ["__class__", "__dict__", "__len__", "__init__", "__doc__", "__module__", "__weakref__", "__name__", "__getattribute__", "__contains__"]:
    def mk():
        return ContraDict({k: "v", "x": {"a": 1}}, silent=True)
    t(f"construct with {k!r}", lambda: type(mk()["x"]).__name__)
    t(f"getattr(cd,{k!r})", lambda: getattr(mk(), k))

# subclass with extra method / property
class Sub(ContraDict):
    def foo(self):
        return "method"

    @property
    def bar(self):
        return "property"

s = Sub({"foo": "v", "bar": "w", "items": "i"}, silent=True)
t("Sub.foo key vs method", lambda: s.foo)
t("Sub.bar key vs property", lambda: s.bar)
t("Sub.items()", lambda: list(s.items()))

# copy / pickle / json
cd = ContraDict({"items": "3", "clear": "all", "nested": {"get": "g"}}, silent=True)
t("json.dumps", lambda: json.dumps(cd))
t("copy.copy", lambda: copy.copy(cd))
t("copy.deepcopy", lambda: copy.deepcopy(cd))
t("pickle roundtrip", lambda: pickle.loads(pickle.dumps(cd)))
t("nested get()", lambda: cd["nested"].get("get"))
t("nested type", lambda: type(cd["nested"]).__name__)
t("plain copy.deepcopy", lambda: copy.deepcopy(ContraDict({"a": {"b": 1}})))
t("plain pickle", lambda: pickle.loads(pickle.dumps(ContraDict({"a": {"b": 1}}))))

# warnings from non-silent construction
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    ContraDict({"clear": "all"})
    print("warnings on non-silent clear:", len(w))

# after-the-fact set of colliding key via setattr / setitem
cd = ContraDict(silent=True)
cd.items = "x"
t("setattr items then items()", lambda: list(cd.items()))
t("setattr items then cd['items']", lambda: cd["items"])
cd["clear"] = "y"
t("setitem clear then clear()", lambda: (cd.clear(), dict(cd))[1])
