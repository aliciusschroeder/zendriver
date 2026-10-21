import pytest
from pytest_mock import MockerFixture

from zendriver.core.connection import Connection


async def test_spy(mocker: MockerFixture) -> None:
    connection = Connection("ws://fake/devtools/browser/fake")
    aclose = mocker.spy(connection, "aclose")
    print(type(aclose))
    with pytest.raises(KeyError):
        async with connection:
            raise KeyError("k")
    aclose.assert_awaited_once_with()
