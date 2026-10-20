import json
doms=[]
for f in ["pkg/package/json/browser_protocol.json","pkg/package/json/js_protocol.json"]:
    doms += json.load(open(f))["domains"]
types={}
for d in doms:
    for t in d.get("types",[]):
        types[d["domain"]+"."+t["id"]]=t
def resolve(ref, dom):
    return types.get(ref if "." in ref else dom+"."+ref)
print("== top-level array types with items")
for d in doms:
    for t in d.get("types",[]):
        if t["type"]=="array":
            it=t["items"]
            kind = None
            if "$ref" in it:
                r=resolve(it["$ref"], d["domain"]); kind = r["type"] + (" enum" if "enum" in r else "") + (" props" if r.get("properties") else "")
            print(d["domain"], t["id"], it, kind)
print("== top-level types with type any or object w/o props, or other odd")
for d in doms:
    for t in d.get("types",[]):
        if t["type"] not in ("string","integer","number","boolean","array","object"):
            print("ODD", d["domain"], t["id"], t["type"])
        if t["type"]=="object" and not t.get("properties"):
            print("objnoprops", d["domain"], t["id"])
        if "enum" in t and t["type"]!="string":
            print("nonstring enum", d["domain"], t["id"])
print("== props/params with type array but items absent, or items with nested array")
def walk_props(d, owner, props):
    for p in props:
        if p.get("type")=="array" and "items" not in p: print("noitems", d["domain"], owner, p["name"])
        if "items" in p and p["items"].get("type")=="array": print("nested array", d["domain"], owner, p["name"])
        if "items" in p and "$ref" not in p["items"] and "type" not in p["items"]: print("items w/o type", owner, p["name"])
        if p.get("type") == "any" or ("type" not in p and "$ref" not in p): print("any-typed", d["domain"], owner, p["name"], p.get("type"))
for d in doms:
    for t in d.get("types",[]): walk_props(d, t["id"], t.get("properties",[]))
    for c in d.get("commands",[]):
        walk_props(d, c["name"]+"(params)", c.get("parameters",[])); walk_props(d, c["name"]+"(returns)", c.get("returns",[]))
    for e in d.get("events",[]): walk_props(d, e["name"]+"(event)", e.get("parameters",[]))
