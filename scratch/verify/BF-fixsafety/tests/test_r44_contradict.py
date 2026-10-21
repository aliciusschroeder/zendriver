import copy
import pickle

import pytest

import zendriver
from zendriver import ContraDict, cdict

print("zendriver imported from", zendriver.__file__)


def test_print_origin() -> None:
    print("zendriver imported from", zendriver.__file__)


@pytest.mark.parametrize("how", ["update", "update_kwargs", "setdefault", "ior"])
def test_nested_dicts_are_converted(how: str) -> None:
    c = cdict()
    if how == "update":
        c.update({"a": {"b": 1}})
    elif how == "update_kwargs":
        c.update(a={"b": 1})
    elif how == "setdefault":
        assert c.setdefault("a", {"b": 1}) == {"b": 1}
        assert c.setdefault("a", {"b": 2}).b == 1
    else:
        before = c
        c |= {"a": {"b": 1}}
        assert c is before
    assert isinstance(c["a"], ContraDict)
    assert c.a.b == 1


@pytest.mark.parametrize(
    "dup",
    [copy.copy, lambda c: pickle.loads(pickle.dumps(c)), copy.deepcopy],
    ids=["copy", "pickle", "deepcopy"],
)
def test_copies_do_not_keep_deleted_keys(dup) -> None:
    c = dup(cdict({"a": {"b": 1}, "z": 2}))
    assert c.a.b == 1
    del c["a"]
    c.pop("z")
    with pytest.raises(AttributeError):
        c.a
    with pytest.raises(AttributeError):
        c.z
    c.n = {"m": 1}
    assert c.n.m == 1 and c["n"].m == 1
    assert vars(c) is c


def test_copy_of_empty() -> None:
    c = copy.copy(cdict())
    c.a = {"b": 1}
    del c["a"]
    with pytest.raises(AttributeError):
        c.a
