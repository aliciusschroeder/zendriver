import sys

p = sys.argv[1]
s = open(p).read()
old = """                except asyncio.CancelledError:
                    # the enable may not have reached the browser, so don't keep
                    # the domain marked as enabled, and let the cancellation through
                    if domain_mod in self.enabled_domains:
                        self.enabled_domains.remove(domain_mod)
                    raise
"""
assert old in s
open(p, "w").write(s.replace(old, ""))
print("applied naive variant")
