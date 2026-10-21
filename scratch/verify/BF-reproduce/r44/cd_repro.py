import copy, pickle, sys
import zendriver
from zendriver import cdict, ContraDict
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], "| ContraDict in __all__:", "ContraDict" in zendriver.__all__, "cdict" in zendriver.__all__)

def attempt(label, fn):
    try:
        print(f"{label}: {fn()!r}")
    except Exception as e:
        print(f"{label}: RAISES {type(e).__name__}: {e}")

print("--- A11.5 update/setdefault/|=")
c = cdict(); c["k"] = {"b": 1}
attempt("control __setitem__ -> c.k.b", lambda: c.k.b)
c = cdict(); c.update({"a": {"b": 1}})
attempt("update -> type(c['a'])", lambda: type(c["a"]).__name__)
attempt("update -> c.a.b", lambda: c.a.b)
c = cdict(); c.update(a={"b": 1})
attempt("update(kw) -> c.a.b", lambda: c.a.b)
c = cdict(); c.setdefault("s", {"b": 1})
attempt("setdefault -> c.s.b", lambda: c.s.b)
c = cdict(); c |= {"o": {"b": 1}}
attempt("|= -> c.o.b", lambda: c.o.b)
attempt("| (operator) -> type(cdict()|{'o':{}})", lambda: type(cdict() | {"o": {"b": 1}}).__name__)

print("--- A11.6 copy.copy / pickle keep deleted keys")
orig = ContraDict({"a": {"b": 1}, "z": 2})
c5 = copy.copy(orig)
del c5["a"]
attempt("copy.copy then del c['a']: 'a' in c", lambda: "a" in c5)
attempt("copy.copy then del c['a']: c.a", lambda: c5.a)
attempt("vars(copy) is copy", lambda: vars(c5) is c5)
c6 = copy.copy(orig); c6.pop("z")
attempt("copy.copy then pop('z'): c.z", lambda: c6.z)
c7 = pickle.loads(pickle.dumps(orig)); del c7["a"]
attempt("pickle round-trip then del c['a']: c.a", lambda: c7.a)
c8 = copy.deepcopy(orig); del c8["a"]
attempt("control deepcopy then del: c.a", lambda: c8.a)
c9 = ContraDict({"a": 1}); del c9["a"]
attempt("control original then del: c.a", lambda: c9.a)
c10 = copy.copy(orig); c10["z"] = 99
attempt("copy.copy then c['z']=99 : c.z", lambda: c10.z)  # works since dict lookup first

print("--- A11.8 assigning existing ContraDict / list stores a copy")
inner = cdict(); c = cdict(); c.child = inner; inner.x = 1
attempt("c.child after inner.x=1", lambda: c.child)
attempt("c.child is inner", lambda: c.child is inner)
lst = []; c.l = lst; lst.append(1)
attempt("c.l after lst.append(1)", lambda: c.l)
d = {}; pc = {}; pc["d"] = d; d["x"] = 1
attempt("control plain dict: pc['d'] after d['x']=1", lambda: pc["d"])
o = ContraDict({"a": {"b": 1}})
attempt("copy.copy shallow? copy(o).a is o.a", lambda: copy.copy(o).a is o.a)
attempt("dict.copy shallow? o.copy()['a'] is o.a", lambda: o.copy()["a"] is o.a)
