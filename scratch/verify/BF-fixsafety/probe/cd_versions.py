import sys, importlib.util, copy, pickle, warnings
spec = importlib.util.spec_from_file_location("cdmod", sys.argv[1]); m = importlib.util.module_from_spec(spec); sys.modules["cdmod"] = m; spec.loader.exec_module(m)
ok = True
for name, dup in [("copy", copy.copy), ("pickle0", lambda c: pickle.loads(pickle.dumps(c, 0))), ("pickle2", lambda c: pickle.loads(pickle.dumps(c, 2))), ("pickle5", lambda c: pickle.loads(pickle.dumps(c, 5))), ("deepcopy", copy.deepcopy)]:
    c = dup(m.ContraDict({"a": {"b": 1}, "z": 2}))
    try:
        assert c.a.b == 1 and isinstance(c.a, m.ContraDict)
        del c["a"]
        try: c.a; ok=False; print(sys.version_info[:2], name, "STALE")
        except AttributeError: pass
    except Exception as e:
        ok=False; print(sys.version_info[:2], name, "ERR", repr(e))
c = m.ContraDict(); c.update({"a": {"b": 1}}); assert c.a.b == 1
c = m.ContraDict(); c.setdefault("a", {"b": 1}); assert c.a.b == 1
c = m.ContraDict(); c |= {"a": {"b": 1}}; assert c.a.b == 1
# key shadowing method names, warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    c = m.ContraDict({"data-x": 1}, silent=True); c2 = copy.copy(c); c3 = pickle.loads(pickle.dumps(c))
    print(sys.version_info[:2], "warnings on copy/pickle of hyphen key:", len(w))
print(sys.version_info[:2], "ALL OK" if ok else "FAIL")
