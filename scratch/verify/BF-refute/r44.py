import copy, pickle, sys
import zendriver
from zendriver import ContraDict, cdict
print("zendriver from", zendriver.__file__, sys.version.split()[0])
def t(label, f):
    try: print(label, "->", repr(f()))
    except Exception as e: print(label, "-> RAISES", type(e).__name__, e)
c = cdict(); c.update({'a': {'b': 1}}); t("update a.b", lambda: c.a.b); print(" type", type(c['a']).__name__)
c = cdict(); c.setdefault('s', {'b': 1}); t("setdefault s.b", lambda: c.s.b)
c = cdict(); c |= {'o': {'b': 1}}; t("|= o.b", lambda: c.o.b)
c = cdict(); c.update(k={'b':1}); t("update kw", lambda: c.k.b)
c = cdict({'a': {'b': 1}}); t("init a.b", lambda: c.a.b)
# A11.6
c0 = ContraDict({'a': {'b': 1}, 'z': 2})
c5 = copy.copy(c0); del c5['a']; t("copy del in", lambda: 'a' in c5); t("copy del attr", lambda: c5.a)
c6 = copy.copy(c0); c6.pop('z'); t("copy pop attr z", lambda: c6.z)
c6['z'] = 3; t("copy reassign z attr", lambda: c6.z)
c6b = copy.copy(c0); c6b['z'] = 9; t("copy setitem then attr (no del)", lambda: c6b.z)
c7 = pickle.loads(pickle.dumps(c0)); del c7['a']; t("pickle del attr", lambda: c7.a)
c8 = copy.deepcopy(c0); del c8['a']; t("deepcopy del attr", lambda: c8.a)
t("vars(copy) is copy", lambda: vars(copy.copy(c0)) is copy.copy(c0))
cx = copy.copy(c0); t("vars(cx) is cx", lambda: vars(cx) is cx)
cy = c0.copy(); t("dict.copy() type", lambda: type(cy).__name__)
# orig
cz = ContraDict({'a':1}); del cz['a']; t("orig del attr", lambda: cz.a)
# A11.8
inner = cdict(); cc = cdict(); cc.child = inner; inner.x = 1; t("child after inner.x=1", lambda: cc.child); t("child is inner", lambda: cc.child is inner)
lst = []; cc.l = lst; lst.append(1); t("l after append", lambda: cc.l)
d = {}; cc.d = d; d['q'] = 1; t("plain dict ref kept?", lambda: cc.d)
pd = {}; pd['child'] = inner; t("plain dict keeps ref", lambda: pd['child'] is inner)
c9 = copy.copy(c0); t("copy shallow c9.a is c0.a", lambda: c9.a is c0.a)
