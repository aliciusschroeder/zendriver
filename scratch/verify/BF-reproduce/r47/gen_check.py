import json, sys
sys.path.insert(0, sys.argv[1])
import generate_cdp as g
spec = json.load(open(sys.argv[2]))
for dom in spec["domains"]:
    for t in dom.get("types", []):
        if (dom["domain"], t["id"]) in (("Target", "TargetFilter"), ("DOM", "NodeId")):
            print(f"--- generator output for {dom['domain']}.{t['id']}:")
            print(g.CdpType.from_json(t, dom["domain"]).generate_code().split('"""')[-1])
    if dom["domain"] == "Runtime":
        t = next(t for t in dom["types"] if t["id"] == "CallArgument")
        p = next(p for p in t["properties"] if p["name"] == "value")
        print("--- CallArgument.value to_json:", g.CdpProperty.from_json(p, "Runtime").generate_to_json("json"))
