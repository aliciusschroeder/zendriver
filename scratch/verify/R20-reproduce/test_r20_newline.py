import zendriver
from zendriver import KeyEvents, KeyPressEvent

def test_char_enter_is_cr():
    print("zendriver from", zendriver.__file__)
    texts = [p["text"] for p in KeyEvents.from_text("a\nb\rc", KeyPressEvent.CHAR)]
    assert texts == ["a", "\r", "b", "\r", "c"], texts
