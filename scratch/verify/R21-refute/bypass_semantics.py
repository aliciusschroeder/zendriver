import os, sys, urllib.request
for k in list(os.environ):
    if k.lower().endswith("_proxy"):
        del os.environ[k]
os.environ["http_proxy"] = "http://proxy.corp.example:3128"
print(sys.version.split()[0], "platform", sys.platform)
for np in [None, "localhost", "localhost,127.0.0.1", "127.0.0.0/8", "127.*", ".0.0.1", "*", "::1,localhost", "127.0.0.1"]:
    os.environ.pop("no_proxy", None)
    if np is not None:
        os.environ["no_proxy"] = np
    h = urllib.request.ProxyHandler()  # default, reads env
    bypass = urllib.request.proxy_bypass("127.0.0.1:9222")
    print(f"no_proxy={np!r:24} proxies={sorted(h.proxies)} proxy_bypass(127.0.0.1:9222)={bool(bypass)}")
