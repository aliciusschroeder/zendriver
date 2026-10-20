import re
from zendriver import cdp
c = cdp.network.Cookie.from_json({"name":"sid","value":"abc","domain":"example.com","path":"/","size":6,"httpOnly":False,"secure":True,"session":True,"priority":"Medium","sameParty":False,"sourceScheme":"Secure","sourcePort":443,"expires":-1})
s = str(c.__dict__)
print(s)
for p in ["session", "secure", "path", "name", "Medium", "example"]:
    print(p, bool(re.compile(p).search(s)))
