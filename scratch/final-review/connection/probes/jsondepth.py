import json, sys
for n in (100, 200, 300, 500, 800, 1000, 2000, 5000, 20000, 100000):
    s = '{"a":' * n + '1' + '}' * n
    try:
        json.loads(s); r = "ok"
    except RecursionError as e:
        r = "RecursionError"
    print(sys.version.split()[0], n, r)
