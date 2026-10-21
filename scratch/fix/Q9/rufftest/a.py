import sys

import pytest


def f() -> BaseException:
    if sys.version_info >= (3, 11):
        return ExceptionGroup("group", [ValueError("inner")])  # noqa: F821
    pytest.skip("ExceptionGroup needs Python 3.11+")
