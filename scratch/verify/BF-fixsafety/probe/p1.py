import copy, pickle, tempfile, pathlib, os, sys
import zendriver
from zendriver import cdict, ContraDict
from zendriver.core import util, config as cfgmod
from zendriver import cdp
print("zendriver from", zendriver.__file__, sys.version.split()[0])
# R44 A11.5
for name, op in [("update", lambda c: c.update({'a': {'b': 1}})),
                 ("setdefault", lambda c: c.setdefault('a', {'b': 1})),
                 ("ior", None)]:
    c = cdict()
    if op: op(c)
    else: c |= {'a': {'b': 1}}
    try: print(name, "->", c.a.b, type(c['a']).__name__)
    except Exception as e: print(name, "-> RAISES", type(e).__name__, e)
# A11.6
c0 = cdict({'a': {'b': 1}, 'z': 2})
for name, fn in [("copy", copy.copy), ("pickle", lambda x: pickle.loads(pickle.dumps(x))), ("deepcopy", copy.deepcopy)]:
    c = fn(c0)
    del c['a']
    try: print(name, "after del: c.a ->", c.a)
    except AttributeError as e: print(name, "after del: AttributeError (correct)")
    c.pop('z')
    try: print(name, "after pop: c.z ->", c.z)
    except AttributeError as e: print(name, "after pop: AttributeError (correct)")
# A11.8
inner = cdict(); c = cdict(); c.child = inner; inner.x = 1
print("A11.8 c.child after inner.x=1:", c.child, "is:", c.child is inner)
lst = []; c.l = lst; lst.append(1); print("A11.8 list:", c.l)
d = {}; c.d = d; d['k']=1; print("A11.8 plain dict:", c.d)
# R45 circle
print("circle(100,0):", [(round(x),round(y)) for x,y in util.circle(100, 0, radius=10, num=4)])
print("circle(100,50):", [(round(x),round(y)) for x,y in util.circle(100, 50, radius=10, num=4)])
# A9.7
td = pathlib.Path(tempfile.mkdtemp(dir=os.environ['S']))
(td/'manifest.json').write_text('{}'); (td/'web').mkdir(); (td/'web'/'manifest.webmanifest').write_text('{}')
cf = cfgmod.Config(headless=True)
cf.add_extension(td)
print("A9.7 root", td, "->", cf._extensions)
import shutil; shutil.rmtree(td)
# A13.3
print("A13.3 str:", str(cdp.dom.NodeId(5)), f"{cdp.dom.BackendNodeId(6)}", "%s" % cdp.network.MonotonicTime(1.5), str(cdp.page.FrameId('abc')))
# A13.1
tf = cdp.target.TargetFilter([cdp.target.FilterEntry(type_='page')])
import json
try: json.dumps(tf.to_json()); print("A13.1 json ok")
except TypeError as e: print("A13.1 TypeError", e)
print("A13.1 from_json elem type:", type(cdp.target.TargetFilter.from_json([{'type':'page'}])[0]).__name__)
print("A13.1 ArrayOfStrings elem StringIndex?", isinstance(cdp.dom_snapshot.ArrayOfStrings.from_json([1])[0], cdp.dom_snapshot.StringIndex))
# A13.4
print("A13.4", cdp.runtime.CallArgument(value=None).to_json())
