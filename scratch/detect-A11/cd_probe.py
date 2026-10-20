import copy, json, pickle, warnings
from zendriver import ContraDict

def t(label, f):
    try:
        print(label, "->", repr(f()))
    except Exception as e:
        print(label, "-> RAISES", type(e).__name__, e)

cd = ContraDict({"keys": 1, "items": [1], "clear": "all", "get": "x", "values": "0;1"}, silent=True)
t("cd.keys()", lambda: cd.keys())
t("cd.items()", lambda: cd.items())
t("cd.clear()", lambda: cd.clear())
t("cd.get('a')", lambda: cd.get("a"))
t("cd.values()", lambda: cd.values())

# update / setdefault bypass wrapping
c2 = ContraDict()
c2.update({"a": {"b": 1}})
t("after update, c2.a.b", lambda: c2.a.b)
c2.setdefault("s", {"b": 1})
t("after setdefault, c2.s.b", lambda: c2.s.b)
c2 |= {"o": {"b": 1}}
t("after |=, c2.o.b", lambda: c2.o.b)
t("ContraDict.fromkeys type", lambda: type(ContraDict.fromkeys(["a"], {"b": 1})["a"]))
# aliasing
inner = ContraDict()
c3 = ContraDict()
c3.child = inner
inner.x = 1
t("c3.child after inner.x=1", lambda: c3.child)
lst = []
c3.l = lst
lst.append(1)
t("c3.l after lst.append", lambda: c3.l)
# copy semantics
c4 = ContraDict({"a": {"b": 1}})
t("type(c4.copy())", lambda: type(c4.copy()))
c5 = copy.copy(c4)
t("copy.copy is shallow? c5.a is c4.a", lambda: c5.a is c4.a)
t("vars(copy) is copy", lambda: vars(c5) is c5)
c5.z = 3
t("copy.copy then set attr; vars(c5) has z", lambda: "z" in vars(c5))
c6 = copy.deepcopy(c4)
t("deepcopy c6.a.b", lambda: c6.a.b)
c7 = pickle.loads(pickle.dumps(c4))
t("pickle c7.a.b", lambda: c7.a.b)
del c7["a"]
t("after del c7['a'], c7.a", lambda: c7.a)
del c5["a"]
t("after del c5['a'] (copy.copy), c5.a", lambda: c5.a)
# snake case claim
c8 = ContraDict({"Protocol-Version": "1.3", "my key": 1}, silent=True)
t("c8 keys", lambda: list(c8))
# silent not propagated to nested
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    ContraDict({"a": {"b-c": 1}}, silent=True)
    print("nested warnings with silent=True:", len(w))
# silent kwarg key
t("ContraDict(silent=1)", lambda: ContraDict(silent=1))
# hasattr on missing
t("hasattr(cd,'zzz')", lambda: hasattr(cd, "zzz"))
# class key
c9 = ContraDict({"class": "x"}, silent=True)
t("c9.__class__", lambda: c9.__class__)
