import json, sys
def f(n):
    s = '{"id":1,"result":{"result":{"type":"object","value":' + '['*n + ']'*n + '}}}'
    try:
        json.loads(s); return True
    except RecursionError:
        return False
def nest(k, n):
    if k == 0: return f(n)
    return nest(k-1, n)
lo = None
for n in range(500, 20001, 1):
    if not nest(15, n):
        lo = n; break
print(sys.version.split()[0], "first failing array depth (15 frames deep):", lo)
