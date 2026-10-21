"""runs a COPY of scripts/generate_cdp.py inside a temporary tree (never the repo)"""
import importlib.util
import json
import os
import pathlib
import shutil
import urllib.request

import pytest

SCRIPT = os.environ.get("GEN_SCRIPT", "/home/user/zendriver/scripts/generate_cdp.py")

SPEC = {
    "browser_protocol.json": {
        "version": {"major": "1", "minor": "3"},
        "domains": [{"domain": "Foo", "types": [{"id": "FooId", "type": "integer", "description": "an id"}]}],
    },
    "js_protocol.json": {
        "version": {"major": "1", "minor": "3"},
        "domains": [{"domain": "Bar", "types": [{"id": "BarId", "type": "string", "description": "an id"}]}],
    },
}


def test_runs_from_a_non_root_cwd(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    (root / "scripts").mkdir(parents=True)
    (root / "zendriver" / "cdp").mkdir(parents=True)
    (root / "zendriver" / "cdp" / "sentinel.py").write_text("")
    script = root / "scripts" / "generate_cdp.py"
    shutil.copy(SCRIPT, script)
    print("generator under test copied from", SCRIPT)

    spec = importlib.util.spec_from_file_location("gen_under_test", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # safety: the copy must operate on the temporary tree only
    assert mod.REPO_ROOT.resolve() == root.resolve()

    def fake_urlretrieve(url: str, filename: str) -> None:
        name = url.rsplit("/", 1)[1]
        pathlib.Path(filename).write_text(json.dumps(SPEC[name]))

    monkeypatch.setattr(urllib.request, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(mod, "format", lambda output_path: None)
    monkeypatch.chdir(root / "scripts")

    mod.main()

    cdp = root / "zendriver" / "cdp"
    assert (cdp / "foo.py").is_file() and (cdp / "bar.py").is_file()
    assert (cdp / "__init__.py").is_file()
    assert "class FooId(int)" in (cdp / "foo.py").read_text()
    assert not list((root / "scripts").glob("*.json")), "spec files left in the cwd"
    assert not list(root.glob("*.json")), "spec files left in the repo root"


SPEC2 = {
    "browser_protocol.json": {
        "version": {"major": "1", "minor": "3"},
        "domains": [
            {
                "domain": "Foo",
                "types": [
                    {"id": "FooId", "type": "integer", "description": "an id"},
                    {"id": "Stamp", "type": "number", "description": "a time"},
                    {
                        "id": "Entry",
                        "type": "object",
                        "description": "an entry",
                        "properties": [{"name": "type", "type": "string", "optional": True}],
                    },
                    {"id": "Filter", "type": "array", "items": {"$ref": "Entry"}, "description": "f"},
                    {"id": "Ids", "type": "array", "items": {"$ref": "FooId"}, "description": "i"},
                ],
                "commands": [
                    {"name": "getThings", "parameters": [{"name": "filter", "$ref": "Filter", "optional": True}]}
                ],
            }
        ],
    },
    "js_protocol.json": {"version": {"major": "1", "minor": "3"}, "domains": []},
}


def test_array_aliases_and_str(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    root = tmp_path / "root"
    (root / "scripts").mkdir(parents=True)
    (root / "zendriver").mkdir()
    script = root / "scripts" / "generate_cdp.py"
    shutil.copy(SCRIPT, script)
    spec = importlib.util.spec_from_file_location("gen_under_test2", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.REPO_ROOT.resolve() == root.resolve()
    for name, content in SPEC2.items():
        (root / name).write_text(json.dumps(content))
    monkeypatch.setattr(mod, "format", lambda output_path: None)
    monkeypatch.chdir(root)
    mod.main()

    pkg_dir = root / "zendriver" / "cdp"
    pspec = importlib.util.spec_from_file_location(
        "gencdp", pkg_dir / "__init__.py", submodule_search_locations=[str(pkg_dir)]
    )
    assert pspec and pspec.loader
    pkg = importlib.util.module_from_spec(pspec)
    sys.modules["gencdp"] = pkg
    try:
        pspec.loader.exec_module(pkg)
        foo = pkg.foo
        f = foo.Filter([foo.Entry(type_="page")])
        assert json.loads(json.dumps(f.to_json())) == [{"type": "page"}]
        cmd = foo.get_things(filter_=f)
        assert json.dumps(next(cmd)["params"]) == '{"filter": [{"type": "page"}]}'
        assert isinstance(foo.Filter.from_json([{"type": "page"}])[0], foo.Entry)
        assert isinstance(foo.Ids.from_json([1])[0], foo.FooId)
        assert str(foo.FooId(5)) == "5" and f"{foo.FooId(5)}" == "5"
        assert str(foo.Stamp(1.5)) == "1.5"
        assert repr(foo.FooId(5)) == "FooId(5)"
    finally:
        for k in [k for k in sys.modules if k == "gencdp" or k.startswith("gencdp.")]:
            del sys.modules[k]
