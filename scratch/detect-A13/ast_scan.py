import ast, pathlib, collections, sys
root = pathlib.Path("/home/user/zendriver/zendriver/cdp")
for f in sorted(root.glob("*.py")):
    if f.name in ("util.py","__init__.py"): continue
    tree = ast.parse(f.read_text())
    top = collections.Counter()
    imported = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            top[node.name] += 1
        elif isinstance(node, ast.ImportFrom):
            for a in node.names: imported.add(a.asname or a.name); top[a.asname or a.name]+=1
        elif isinstance(node, ast.Import):
            for a in node.names: imported.add(a.asname or a.name); top[a.asname or a.name]+=1
    dups = [k for k,v in top.items() if v>1]
    if dups: print(f.name, "DUP top-level:", dups)
    globals_ = set(top)
    for node in tree.body:
        funcs = []
        if isinstance(node, ast.FunctionDef): funcs.append((node.name,node))
        if isinstance(node, ast.ClassDef):
            for n in node.body:
                if isinstance(n, ast.FunctionDef): funcs.append((node.name+"."+n.name,n))
        for name, fn in funcs:
            argnames = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
            used = set()
            for stmt in fn.body:
                for n in ast.walk(stmt):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load): used.add(n.id)
            shadow = argnames & globals_
            if shadow:
                print(f.name, name, "params shadow globals:", shadow, "used in body:", shadow & used)
            bad = argnames & {"params","cmd_dict","json"} 
            if bad and not name.endswith("from_json"):
                print(f.name, name, "params named reserved locals:", bad)
